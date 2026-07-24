"""The `lexiqr` command line — the no-Python interface for lexicon authors.

This is the thin shell: it parses arguments, reads a file, parses JSON, calls
lexiqr's public API, hands the typed result to a pure renderer, and maps the
outcome to an exit code. It holds no validation logic and no matching logic
(ADR 0002) — if the CLI ever needs a private import, the public API is missing
something.

Two error families are kept visibly distinct so an author can tell "your path
is wrong" from "your lexicon is wrong" at a glance:

- CLI-level failures — the file is missing / unreadable, or not valid JSON —
  are the shell's own, and exit with ``EXIT_CLI_ERROR``.
- Lexicon-level failures are core's structured `ValidationError`s, rendered
  verbatim in substance, and exit with ``EXIT_INVALID_LEXICON``.

Stream discipline: results and confirmations go to stdout; every diagnostic and
error goes to stderr, so an author can pipe or capture just the part they need.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from lexiqr import EntityResolver, ValidationError
from lexiqr.cli._report import render_match_report
from lexiqr.cli._validation import render_valid_lexicon, render_validation_errors

#: The lexicon loaded, resolved, or matched — nothing went wrong.
EXIT_OK = 0
#: The file was read and parsed, but core rejected it as an invalid lexicon.
EXIT_INVALID_LEXICON = 1
#: A CLI-level failure the shell owns: the path is missing / unreadable, or the
#: file is not valid JSON. Distinct from ``EXIT_INVALID_LEXICON`` so a script
#: can tell a broken path from a broken lexicon.
EXIT_CLI_ERROR = 3
#: `try` ran against a valid lexicon but the report was empty. Distinct from
#: every load-failure code so a regression script can tell "the prompt did not
#: resolve" from "the lexicon could not be loaded". (Exit code 2 is left to
#: argparse for its own usage errors.)
EXIT_NO_MATCH = 4


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        return _validate(args.lexicon)
    return _try(args)


def _validate(source: str) -> int:
    document, load_code = _load_document(source)
    if document is None:
        return load_code

    errors = _lexicon_errors(document)
    if errors is not None:
        print(render_validation_errors(source, errors), file=sys.stderr)
        return EXIT_INVALID_LEXICON

    print(render_valid_lexicon(source))
    return EXIT_OK


def _try(args: argparse.Namespace) -> int:
    document, load_code = _load_document(args.lexicon)
    if document is None:
        return load_code

    try:
        resolver = EntityResolver.from_dict(document)
    except ValidationError as invalid:
        print(render_validation_errors(args.lexicon, [invalid]), file=sys.stderr)
        return EXIT_INVALID_LEXICON

    report = resolver.transform(args.prompt, args.locale)
    print(render_match_report(report))
    return EXIT_OK if report.matches else EXIT_NO_MATCH


def _load_document(source: str) -> tuple[Any | None, int]:
    """Read and parse `source`, or report a CLI-level failure.

    Returns the parsed document and ``EXIT_OK`` on success; ``None`` and
    ``EXIT_CLI_ERROR`` on a missing / unreadable file or malformed JSON, having
    already written the diagnostic to stderr. These are the shell's own
    failures, phrased so they cannot be mistaken for a lexicon error.
    """
    try:
        text = Path(source).read_text(encoding="utf-8")
    except OSError as unreadable:
        reason = unreadable.strerror or str(unreadable)
        print(f"lexiqr: cannot read {source}: {reason}", file=sys.stderr)
        return None, EXIT_CLI_ERROR

    try:
        return json.loads(text), EXIT_OK
    except json.JSONDecodeError as malformed:
        print(
            f"lexiqr: {source} is not valid JSON: {malformed.msg} "
            f"(line {malformed.lineno}, column {malformed.colno}).",
            file=sys.stderr,
        )
        return None, EXIT_CLI_ERROR


def _lexicon_errors(document: Any) -> list[ValidationError] | None:
    """Load `document` through the public API, returning any faults it raises.

    ``None`` means the lexicon is valid. A list — one fault today, since core
    surfaces the first — means it is not. The shell never inspects the fault; it
    hands it straight to the renderer.
    """
    try:
        EntityResolver.from_dict(document)
    except ValidationError as invalid:
        return [invalid]
    return None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lexiqr",
        description="Inspect and check lexicon files without writing Python.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    validate_command = subcommands.add_parser(
        "validate",
        help="Check whether a lexicon file is valid.",
    )
    validate_command.add_argument("lexicon", help="Path to a lexicon JSON file.")

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
