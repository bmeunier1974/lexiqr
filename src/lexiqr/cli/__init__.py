"""The `lexiqr` command line — the no-Python interface for lexicon authors.

This is the thin shell: it parses arguments, asks lexiqr's public API to load
the lexicon, hands the typed result to a pure renderer, and maps the outcome to
an exit code. It holds no loading logic, no validation logic and no matching
logic (ADR 0002) — it never opens the file or parses the JSON itself, because a
second reading of the same file is a second chance to phrase the same failure
differently. If the CLI ever needs a private import, the public API is missing
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
import sys

from lexiqr import EntityResolver, Lexicon, MalformedDocumentError, ValidationError
from lexiqr.cli._report import render_match_report
from lexiqr.cli._validation import (
    render_malformed_document,
    render_unreadable_source,
    render_valid_lexicon,
    render_validation_errors,
)

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
    lexicon, failure = _load(source)
    if lexicon is None:
        return failure

    print(render_valid_lexicon(source))
    return EXIT_OK


def _try(args: argparse.Namespace) -> int:
    lexicon, failure = _load(args.lexicon)
    if lexicon is None:
        return failure

    report = EntityResolver(lexicon).transform(args.prompt, args.locale)
    print(render_match_report(report))
    return EXIT_OK if report.matches else EXIT_NO_MATCH


def _load(source: str) -> tuple[Lexicon | None, int]:
    """Load `source` through lexiqr's public API, or report why it could not.

    The file is read, parsed and validated exactly once, by core, for both
    commands: `validate` says whether that load succeeded, and `try` matches
    against the very lexicon it returned — so validation and matching cannot
    describe two different readings of one file within a single run.

    Returns the lexicon and ``EXIT_OK``, or ``None`` and the exit code the
    failure earns, having already written the diagnostic to stderr. The three
    failures are told apart by the type core raises, never by reading its
    message: an unreadable path and a file that is not JSON are the shell's own
    CLI-level failures, while a document core rejected is a lexicon error.
    """
    try:
        return Lexicon.from_file(source), EXIT_OK
    except OSError as unreadable:
        print(render_unreadable_source(source, unreadable), file=sys.stderr)
        return None, EXIT_CLI_ERROR
    except MalformedDocumentError as malformed:
        print(render_malformed_document(malformed), file=sys.stderr)
        return None, EXIT_CLI_ERROR
    except ValidationError as invalid:
        print(render_validation_errors(source, [invalid]), file=sys.stderr)
        return None, EXIT_INVALID_LEXICON


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lexiqr",
        description="Check and try lexicon files from the terminal, without "
        "writing Python.",
    )
    subcommands = parser.add_subparsers(
        dest="command",
        required=True,
        metavar="{validate,try}",
        title="commands",
    )

    validate_command = subcommands.add_parser(
        "validate",
        help="Check whether a lexicon file is valid.",
        description="Load a lexicon and report whether it is valid, with the "
        "same errors the library raises at load time.",
    )
    validate_command.add_argument(
        "lexicon",
        help="Path to the lexicon file (a JSON document) to check.",
    )

    try_command = subcommands.add_parser(
        "try",
        help="Resolve a prompt against a lexicon and print the match report.",
        description="Resolve a prompt, written in a locale, against a lexicon "
        "and print the full match report.",
    )
    try_command.add_argument(
        "lexicon",
        help="Path to the lexicon file (a JSON document) to resolve against.",
    )
    try_command.add_argument(
        "--locale",
        required=True,
        metavar="LOCALE",
        help="The locale the prompt is written in, as a BCP 47 tag "
        '(e.g. "de-DE"); passed to the lexicon\'s fallback chain unchanged.',
    )
    try_command.add_argument(
        "prompt",
        help="The prompt: the free-form user text to resolve against the lexicon.",
    )

    return parser
