"""CLI argument parsing for the case classifier."""

from __future__ import annotations

import argparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify a legal case to identify applicable OpenFisca-indexed Swiss laws.",
    )
    parser.add_argument(
        "case",
        nargs="?",
        default=None,
        help="Natural-language case description. If omitted, you will be prompted interactively.",
    )
    parser.add_argument(
        "--generate", "-g",
        metavar="ARTICLE",
        default=None,
        help="Directly generate OpenFisca code for a given article reference (e.g. 'OR Art. 41').",
    )
    parser.add_argument(
        "--text", "-t",
        default=None,
        help="Custom legal text to use with --generate (e.g. French version of the article).",
    )

    args = parser.parse_args()

    if args.text and not args.generate:
        parser.error("--text can only be used together with --generate")
    if args.generate and args.case:
        parser.error("--generate and positional case argument are mutually exclusive")

    return args


def get_case_description(args: argparse.Namespace) -> str:
    """Return the case description from CLI args or interactive prompt."""
    if args.case:
        return args.case
    print("Enter a case description (press Enter twice to submit):")
    lines: list[str] = []
    while True:
        line = input()
        if line == "" and lines:
            break
        lines.append(line)
    return "\n".join(lines)
