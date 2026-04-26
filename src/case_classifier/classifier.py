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
             "extracted from the case, e.g. {'OR Art. 41': {'damage_caused': true, ...}}"
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
