"""Static validation for generated OpenFisca code and parameter YAML."""

from __future__ import annotations

import ast
import re

import yaml

_CODE_FENCE_RE = re.compile(r"^```\w*\n?|```$", re.MULTILINE)


def strip_code_fences(text: str) -> str:
    """Remove markdown code fences (```python, ```yaml, etc.) from text."""
    return _CODE_FENCE_RE.sub("", text.strip())


def validate_python(code: str) -> tuple[bool, str]:
    """Validate generated Python code via ast.parse and structural checks.

    Returns (is_valid, error_message).
    """
    errors: list[str] = []

    try:
        ast.parse(code)
    except SyntaxError as exc:
        return False, f"SyntaxError: {exc}"

    if not re.search(r"class\s+\w+\(Variable\)", code):
        errors.append("Missing 'class ...(Variable)' declaration")

    if "def formula(" not in code:
        errors.append("Missing 'def formula(' method")

    if "definition_period" not in code:
        errors.append("Missing 'definition_period' attribute")

    if errors:
        return False, "; ".join(errors)
    return True, ""


def validate_yaml(text: str) -> tuple[bool, str]:
    """Validate generated parameter YAML.

    Returns (is_valid, error_message).
    """
    try:
        parsed = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return False, f"YAML parse error: {exc}"

    if parsed is None:
        return False, "YAML is empty"

    if not re.search(r"\d{4}-\d{2}-\d{2}", text):
        return False, "Missing dated entry (YYYY-MM-DD)"

    return True, ""


def validate_generated_code(code: str, yaml_text: str) -> tuple[bool, list[str]]:
    """Validate both Python code and parameter YAML.

    Returns (all_valid, list_of_errors).
    """
    errors: list[str] = []

    py_ok, py_err = validate_python(code)
    if not py_ok:
        errors.append(f"Python: {py_err}")

    yaml_ok, yaml_err = validate_yaml(yaml_text)
    if not yaml_ok:
        errors.append(f"YAML: {yaml_err}")

    return len(errors) == 0, errors
