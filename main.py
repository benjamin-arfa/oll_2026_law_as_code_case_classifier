"""Entry point for the case classifier."""

from __future__ import annotations

import json
import os
import re

import dspy
from dotenv import load_dotenv

from case_classifier.classifier import CaseClassifier
from case_classifier.cli import get_case_description, parse_args
from case_classifier.code_generator import (
    CodeGenerationResult,
    LegalTransformer,
    generate_code_for_laws,
    generate_code_for_single_law,
)
from case_classifier.law_index import format_law_index_for_prompt, get_all_laws, get_law_by_reference
from case_classifier.openjustice_lm import OpenJusticeLM


def configure_lm() -> dspy.LM:
    """Configure the LLM based on environment variables."""
    provider = os.getenv("LLM_PROVIDER", "cerebras").lower()

    if provider == "openjustice":
        return OpenJusticeLM(
            model=os.getenv("OPENJUSTICE_MODEL", "gpt-5.4-nano"),
            api_key=os.getenv("OPENJUSTICE_API_KEY", ""),
        )

    # Default: Cerebras via litellm
    return dspy.LM(
        model=f"cerebras/{os.getenv('CEREBRAS_MODEL', 'qwen-3-235b-a22b-instruct-2507')}",
        api_key=os.getenv("CEREBRAS_API_KEY", ""),
    )


def parse_applicable_laws(raw: str) -> list[str]:
    """Parse the applicable_laws output from Stage 1 into a list of strings.

    Tries JSON first, falls back to regex extraction of quoted strings.
    """
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except (json.JSONDecodeError, TypeError):
        pass

    # Regex fallback: extract quoted strings like 'OR Art. 41'
    matches = re.findall(r"['\"]([^'\"]+)['\"]", raw)
    return matches


def print_classification_result(result) -> None:
    """Display the Stage 1 classification result."""
    print("\n" + "=" * 60)
    print("SYLLOGISTIC REASONING")
    print("=" * 60)
    print(result.syllogistic_reasoning)

    print("\n" + "-" * 60)
    print("APPLICABLE LAWS")
    print("-" * 60)
    print(result.applicable_laws)

    print("\n" + "-" * 60)
    print("INPUT PARAMETERS")
    print("-" * 60)
    print(result.input_parameters)
    print("=" * 60)


def print_code_generation_results(results: list[CodeGenerationResult]) -> None:
    """Display the Stage 2 code generation results."""
    print("\n" + "=" * 60)
    print("GENERATED OPENFISCA CODE")
    print("=" * 60)

    for r in results:
        status = "validated" if r.validation_passed else "FAILED"
        attempt_label = "attempt" if r.attempts == 1 else "attempts"
        print(f"\n--- {r.article_reference} [{status}, {r.attempts} {attempt_label}] ---")

        if r.validation_passed:
            print("\nPython Variable:")
            print(r.openfisca_variable)

            print("\nParameter YAML:")
            print(r.parameter_yaml)
        else:
            print(f"\nError: {r.error}")
            if r.openfisca_variable:
                print("\nLast Python attempt:")
                print(r.openfisca_variable)

    print("=" * 60)


def run_generate_mode(args) -> None:
    """Directly generate OpenFisca code for a single article reference."""
    article_ref = args.generate

    # Resolve legal text
    if args.text:
        legal_text = args.text
    else:
        law = get_law_by_reference(article_ref)
        if law is None:
            print(
                f"Error: Article '{article_ref}' not found in law index.\n"
                f"Hint: use --text to supply the legal text manually."
            )
            return
        legal_text = law["legal_text"].strip()

    print(f"Generating OpenFisca code for {article_ref}...\n")

    lm = configure_lm()
    dspy.configure(lm=lm)

    transformer = LegalTransformer()
    result = generate_code_for_single_law(
        transformer=transformer,
        legal_text=legal_text,
        article_reference=article_ref,
    )

    print_code_generation_results([result])


def main() -> None:
    load_dotenv()

    args = parse_args()

    if args.generate:
        run_generate_mode(args)
        return

    case_description = get_case_description(args)

    print(f"Case: {case_description}\n")
    print("Loading law index...")
    laws = get_all_laws()
    law_index = format_law_index_for_prompt(laws)

    print("Configuring LLM...")
    lm = configure_lm()
    dspy.configure(lm=lm)

    # Stage 1: Classification
    print("Classifying case...\n")
    classifier = CaseClassifier()
    result = classifier(case_description=case_description, law_index=law_index)

    print_classification_result(result)

    # Stage 2: Code generation
    applicable_law_refs = parse_applicable_laws(result.applicable_laws)
    if not applicable_law_refs:
        print("\nNo applicable laws identified — skipping code generation.")
        return

    print(f"\nGenerating OpenFisca code for {len(applicable_law_refs)} law(s)...")
    code_results = generate_code_for_laws(applicable_law_refs, laws=laws)

    print_code_generation_results(code_results)


if __name__ == "__main__":
    main()
