"""Variable registry — tracks known OpenFisca variables for cross-reference context."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class VariableInfo:
    """Metadata for a registered OpenFisca variable."""

    name: str
    article_ref: str
    value_type: str = "float"
    entity: str = "Person"
    definition_period: str = "MONTH"
    label: str = ""


class VariableRegistry:
    """Accumulates known variables and renders compact context for the LLM prompt."""

    def __init__(self) -> None:
        self._variables: dict[str, VariableInfo] = {}

    def register(self, info: VariableInfo) -> None:
        """Register a variable. Overwrites if same name already exists."""
        self._variables[info.name] = info

    def get(self, name: str) -> VariableInfo | None:
        return self._variables.get(name)

    def all_names(self) -> list[str]:
        return list(self._variables)

    def __len__(self) -> int:
        return len(self._variables)

    def render(self) -> str:
        """Render a compact summary of all registered variables for LLM context."""
        if not self._variables:
            return ""

        lines = ["Available OpenFisca variables you may reference with person(\"<name>\", period):"]
        for info in self._variables.values():
            desc = f"  - {info.name} ({info.value_type}, {info.entity}, {info.definition_period})"
            if info.label:
                desc += f" — {info.label}"
            desc += f"  [from {info.article_ref}]"
            lines.append(desc)
        return "\n".join(lines)


_CLASS_NAME_RE = re.compile(r"class\s+(\w+)\s*\(\s*Variable\s*\)")
_VALUE_TYPE_RE = re.compile(r"value_type\s*=\s*(\w+)")
_ENTITY_RE = re.compile(r"entity\s*=\s*(\w+)")
_PERIOD_RE = re.compile(r"definition_period\s*=\s*(\w+)")
_LABEL_RE = re.compile(r'label\s*=\s*["\']([^"\']+)["\']')


def extract_variable_info(code: str, article_ref: str) -> VariableInfo | None:
    """Extract VariableInfo from generated OpenFisca Python code."""
    name_match = _CLASS_NAME_RE.search(code)
    if not name_match:
        return None

    name = name_match.group(1)
    vtype = _VALUE_TYPE_RE.search(code)
    entity = _ENTITY_RE.search(code)
    period = _PERIOD_RE.search(code)
    label = _LABEL_RE.search(code)

    return VariableInfo(
        name=name,
        article_ref=article_ref,
        value_type=vtype.group(1) if vtype else "float",
        entity=entity.group(1) if entity else "Person",
        definition_period=period.group(1) if period else "MONTH",
        label=label.group(1) if label else "",
    )
