"""Load and manage the YAML law index catalogue."""

from __future__ import annotations

from pathlib import Path

import yaml

_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "laws"


def get_all_laws(data_dir: Path | None = None) -> list[dict]:
    """Load all YAML law definitions from *data_dir*."""
    directory = data_dir or _DATA_DIR
    laws: list[dict] = []
    for path in sorted(directory.glob("*.yaml")):
        with open(path, encoding="utf-8") as fh:
            laws.append(yaml.safe_load(fh))
    return laws


def get_law_by_reference(article_reference: str, laws: list[dict] | None = None) -> dict | None:
    """Look up a single law by its article reference string."""
    if laws is None:
        laws = get_all_laws()
    for law in laws:
        if law["article_reference"] == article_reference:
            return law
    return None


def format_law_index_for_prompt(laws: list[dict] | None = None) -> str:
    """Format the law catalogue as text suitable for an LLM prompt."""
    if laws is None:
        laws = get_all_laws()

    sections: list[str] = []
    for law in laws:
        params = "\n".join(
            f"    - {p['name']} ({p['type']}): {p['description']}"
            for p in law.get("input_parameters", [])
        )
        section = (
            f"### {law['article_reference']} — {law['law_name']}\n"
            f"Legal text:\n{law['legal_text'].strip()}\n\n"
            f"OpenFisca variable: {law['openfisca_variable']}\n"
            f"Input parameters:\n{params}"
        )
        sections.append(section)

    return "\n\n---\n\n".join(sections)
