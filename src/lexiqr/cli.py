"""The `lexiqr` command line — the no-Python interface for lexicon authors.

This module may only call lexiqr's public API, never private modules (ADR 0002):
if the CLI ever needs a private import, the public API is missing something.
"""

from __future__ import annotations

import argparse

from lexiqr import EntityResolver, MatchReport


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    resolver = EntityResolver.from_file(args.lexicon)
    report = resolver.transform(args.prompt, args.locale)
    print(_render(report))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lexiqr",
        description="Inspect and check lexicon files without writing Python.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    try_command = subcommands.add_parser(
        "try",
        help="Resolve a prompt against a lexicon and print the match report.",
    )
    try_command.add_argument("lexicon", help="Path to a lexicon JSON file.")
    try_command.add_argument(
        "--locale",
        required=True,
        help='BCP 47 tag the prompt is written in, e.g. "de-DE".',
    )
    try_command.add_argument("prompt", help="The free-form text to resolve.")

    return parser


def _render(report: MatchReport) -> str:
    lines = [f'prompt: "{report.prompt}"', f"locale: {report.locale}"]
    if not report.matches:
        lines.append("matches: none")
        return "\n".join(lines)

    lines.append(f"matches: {len(report.matches)}")
    lines.extend(
        f'  {match.canonical_id} ← "{match.surface_form}" '
        f"[{match.span[0]}:{match.span[1]}]"
        for match in report.matches
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
