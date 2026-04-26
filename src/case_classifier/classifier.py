"""DSPy module for syllogistic legal case classification."""

from __future__ import annotations

import dspy


class CaseClassification(dspy.Signature):
    """Classify a legal case using syllogistic reasoning to identify
    applicable Swiss laws indexed in OpenFisca and their required
    input parameters."""

    case_description: str = dspy.InputField(
        desc="Natural language description of a legal case or situation"
    )
    law_index: str = dspy.InputField(
        desc="Catalogue of available OpenFisca-indexed Swiss laws with their input parameters"
    )
    syllogistic_reasoning: str = dspy.OutputField(
        desc="For each applicable law: Major premise (the legal rule), "
             "Minor premise (facts from the case matching the rule's conditions), "
             "Conclusion (whether the law applies and why)"
    )
    applicable_laws: str = dspy.OutputField(
        desc="JSON list of applicable law references, e.g. ['OR Art. 41', 'AHVG Art. 5']"
    )
    input_parameters: str = dspy.OutputField(
        desc="JSON object mapping each applicable law to its input parameter values "
             "extracted from the case. "
             "CRITICAL RULES: "
             "1) For enum parameters (shown with [value1/value2/...]), you MUST use one of the exact listed values verbatim. "
             'Read the "= description" after each value to understand its meaning. '
             "2) INFER values from context: if someone says 'university studies' without mentioning a prior degree, "
             'use "erstausbildung" (first education), NOT "zweite_hochschulausbildung" (which means second university degree after already completing one). '
             '3) If someone says "living in Bern", infer wohnsitz_grundlage="elterlicher_wohnsitz" (default student domicile in Bern). '
             '4) If someone mentions "university"/"Hochschule", infer ausbildungsstufe="tertiaerstufe" and ausbildungsstaette_anerkannt=true. '
             "5) Only use null for values truly impossible to determine from context."
    )


class CaseClassifier(dspy.Module):
    """Classify a case description against the law index using chain-of-thought."""

    def __init__(self):
        super().__init__()
        self.classify = dspy.ChainOfThought(CaseClassification)

    def forward(self, case_description: str, law_index: str):
        return self.classify(
            case_description=case_description,
            law_index=law_index,
        )
