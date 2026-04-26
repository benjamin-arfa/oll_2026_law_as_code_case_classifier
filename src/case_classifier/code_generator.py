"""Stage 2 — generate OpenFisca code for each applicable law identified by the classifier."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import dspy

from case_classifier.law_index import get_all_laws, get_law_by_reference
from case_classifier.registry import VariableRegistry, extract_variable_info
from case_classifier.validator import strip_code_fences, validate_generated_code

log = logging.getLogger(__name__)

MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# DSPy signature & module
# ---------------------------------------------------------------------------

class LegalToCode(dspy.Signature):
    """Transform a Swiss legal article into executable OpenFisca code.

    Given the full text of a Swiss federal legal article, produce a Python
    Variable class for OpenFisca and a YAML parameter snippet that faithfully
    implement the legal logic.

    The YAML parameter snippet must always be non-empty. For articles with
    numeric rules, define rate or threshold parameters. For articles with
    boolean conditions (e.g. tort liability, eligibility), define boolean
    indicator parameters (value: true/false) with dated entries.
    """

    legal_article_text: str = dspy.InputField(
        desc="Full text of a Swiss federal legal article (German, French, or Italian)"
    )
    article_reference: str = dspy.InputField(
        desc="Article identifier, e.g. 'AHVG Art. 5' or 'OR Art. 41'"
    )
    available_variables: str = dspy.InputField(
        desc="Already-defined OpenFisca variables that may be referenced via person(\"<name>\", period). Empty string if none.",
        default="",
    )
    openfisca_variable: str = dspy.OutputField(
        desc="Python class inheriting from Variable with a formula() method implementing the legal logic"
    )
    parameter_yaml: str = dspy.OutputField(
        desc="YAML snippet defining OpenFisca parameters referenced by the variable. "
             "Parameters include numeric values (rates, thresholds, amounts) AND boolean "
             "indicators or conditions (e.g. eligibility flags, legal conditions). "
             "Every variable must have at least one parameter with a dated entry."
    )
    reasoning: str = dspy.OutputField(
        desc="Step-by-step explanation of how the legal text maps to the code"
    )


class LegalTransformer(dspy.Module):
    """Chain-of-thought module that reasons through legal text before generating code."""

    def __init__(self):
        super().__init__()
        self.transform = dspy.ChainOfThought(LegalToCode)

    def forward(
        self,
        legal_article_text: str,
        article_reference: str,
        available_variables: str = "",
    ):
        return self.transform(
            legal_article_text=legal_article_text,
            article_reference=article_reference,
            available_variables=available_variables,
        )


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class CodeGenerationResult:
    """Result of code generation for a single law article."""

    article_reference: str
    openfisca_variable: str = ""
    parameter_yaml: str = ""
    reasoning: str = ""
    validation_passed: bool = False
    error: str = ""
    attempts: int = 0


# ---------------------------------------------------------------------------
# Single-law generator with retry
# ---------------------------------------------------------------------------

def generate_code_for_single_law(
    transformer: LegalTransformer,
    legal_text: str,
    article_reference: str,
    available_variables: str = "",
    max_retries: int = MAX_RETRIES,
) -> CodeGenerationResult:
    """Generate OpenFisca code for a single law, retrying on validation failure."""
    last_errors: list[str] = []
    input_text = legal_text
    code = ""
    yaml_text = ""
    reasoning = ""

    for attempt in range(1, max_retries + 1):
        if last_errors:
            error_feedback = "; ".join(last_errors)
            input_text = (
                f"{legal_text}\n\n"
                f"[PREVIOUS ATTEMPT FAILED: {error_feedback}. "
                f"Please fix these issues in your next attempt.]"
            )

        try:
            prediction = transformer(
                legal_article_text=input_text,
                article_reference=article_reference,
                available_variables=available_variables,
            )
        except Exception as exc:
            log.error("LLM call failed for %s (attempt %d): %s", article_reference, attempt, exc)
            last_errors = [str(exc)]
            continue

        code = strip_code_fences(prediction.openfisca_variable)
        yaml_text = strip_code_fences(prediction.parameter_yaml)
        reasoning = prediction.reasoning

        valid, errors = validate_generated_code(code, yaml_text)

        if valid:
            return CodeGenerationResult(
                article_reference=article_reference,
                openfisca_variable=code,
                parameter_yaml=yaml_text,
                reasoning=reasoning,
                validation_passed=True,
                attempts=attempt,
            )

        log.warning(
            "Validation failed for %s (attempt %d/%d): %s",
            article_reference, attempt, max_retries, errors,
        )
        last_errors = errors

    # All retries exhausted
    return CodeGenerationResult(
        article_reference=article_reference,
        openfisca_variable=code,
        parameter_yaml=yaml_text,
        reasoning=reasoning,
        validation_passed=False,
        error="; ".join(last_errors),
        attempts=max_retries,
    )


# ---------------------------------------------------------------------------
# Multi-law orchestrator
# ---------------------------------------------------------------------------

def generate_code_for_laws(
    applicable_law_refs: list[str],
    laws: list[dict] | None = None,
) -> list[CodeGenerationResult]:
    """Generate OpenFisca code for each applicable law reference.

    Processes laws in order, accumulating a VariableRegistry so later
    laws can reference variables defined by earlier ones.
    """
    if laws is None:
        laws = get_all_laws()

    transformer = LegalTransformer()
    registry = VariableRegistry()
    results: list[CodeGenerationResult] = []

    for ref in applicable_law_refs:
        law = get_law_by_reference(ref, laws)
        if law is None:
            log.warning("Law reference '%s' not found in index — skipping", ref)
            results.append(CodeGenerationResult(
                article_reference=ref,
                error=f"Law reference '{ref}' not found in index",
                attempts=0,
            ))
            continue

        legal_text = law["legal_text"].strip()
        context = registry.render()

        print(f"  Generating code for {ref}...")
        result = generate_code_for_single_law(
            transformer=transformer,
            legal_text=legal_text,
            article_reference=ref,
            available_variables=context,
        )
        results.append(result)

        # Register successful variable for cross-references
        if result.validation_passed:
            info = extract_variable_info(result.openfisca_variable, ref)
            if info:
                registry.register(info)

    return results
