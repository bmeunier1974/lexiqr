"""Cross-platform report equality: the third determinism layer, as a CI gate.

Determinism within a process and across processes is checked by ordinary tests
(see tests/test_determinism_*). The layer they cannot reach is *across the
matrix*: the same lexicon and prompt must serialize identically on Linux, macOS,
and Windows, and on every supported Python. This script is what the matrix job
runs on each cell — it resolves a fixed fixture set, canonically serializes every
report through the public API (`serialize_report`, ADR 0002 / story #51), and
compares the result to a committed golden that every platform must reproduce
byte-for-byte.

Comparing each cell to one committed golden *is* comparing the cells to each
other: if every platform equals the golden, every platform equals every other.
A divergence fails the cell, and because the job is named by its OS and Python,
the red X names the platform — and this script prints the first differing report
so the failure is a diff, not a mystery.

Deliberately stdlib-plus-lexiqr and import-light: it must run against the
installed package on a bare CI runner, exactly as an integrating developer's own
environment would. Regenerate the golden with `--write` after an intended change
to resolution behavior; a patch that changes it unintentionally is the
regression this gate exists to catch.
"""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

from lexiqr import EntityResolver, serialize_report

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN = Path(__file__).resolve().parent / "report_equality.golden.json"

#: The fixed fixture set: (lexicon path relative to the repo root, prompt,
#: locale). Chosen to exercise the places a platform could plausibly diverge —
#: accent folding, casefolding, a script-preserving language (Arabic), fuzzy
#: correction, locale fallback, plurals, and the empty result — not just the
#: happy path. The order is fixed, so the serialized block is deterministic.
FIXTURES: tuple[tuple[str, str, str], ...] = (
    ("examples/flooff.lexicon.json", "wo ist flooff", "de-DE"),
    ("schema/fixtures/valid/acme-multilingual.lexicon.json", "wo ist flooff", "de-DE"),
    ("schema/fixtures/valid/acme-multilingual.lexicon.json", "floof bitte", "de-DE"),
    (
        "schema/fixtures/valid/acme-multilingual.lexicon.json",
        "i need a widget",
        "en-GB",
    ),
    (
        "schema/fixtures/valid/acme-multilingual.lexicon.json",
        "show me the invoices",
        "en-GB",
    ),
    (
        "schema/fixtures/valid/acme-multilingual.lexicon.json",
        "i lost my TICKET",
        "en-GB",
    ),
    ("schema/fixtures/valid/acme-multilingual.lexicon.json", "wo ist منتج", "ar-EG"),
    ("schema/fixtures/valid/medien-de.lexicon.json", "wo ist flooff", "de-AT"),
    ("schema/fixtures/valid/medien-de.lexicon.json", "die rechnung", "de-AT"),
    ("examples/flooff.lexicon.json", "", "de-DE"),
)


def build_block() -> list[str]:
    """The canonical serialization of every fixture's report, in fixed order."""
    resolvers: dict[str, EntityResolver] = {}
    reports: list[str] = []
    for relative_path, prompt, locale in FIXTURES:
        resolver = resolvers.get(relative_path)
        if resolver is None:
            resolver = EntityResolver.from_file(REPO_ROOT / relative_path)
            resolvers[relative_path] = resolver
        reports.append(serialize_report(resolver.transform(prompt, locale)))
    return reports


def _here() -> str:
    return f"{platform.system()} / Python {platform.python_version()}"


def main(argv: list[str]) -> int:
    reports = build_block()
    block = json.dumps(reports, ensure_ascii=True)

    if "--write" in argv:
        GOLDEN.write_text(block + "\n", encoding="utf-8")
        print(f"Wrote golden ({len(reports)} reports) to {GOLDEN.name}.")
        return 0

    if not GOLDEN.exists():
        print(
            f"Golden {GOLDEN.name} is missing; regenerate it with --write.",
            file=sys.stderr,
        )
        return 2

    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    if reports == golden:
        print(
            f"OK: {_here()} matches the cross-platform golden ({len(reports)} reports)."
        )
        return 0

    print(
        f"FAIL: resolution on {_here()} diverges from the cross-platform golden.",
        file=sys.stderr,
    )
    for index, produced in enumerate(reports):
        expected = golden[index] if index < len(golden) else "<missing>"
        if produced != expected:
            path, prompt, locale = FIXTURES[index]
            print(
                f"  first divergence at fixture #{index}: {path} {prompt!r} [{locale}]",
                file=sys.stderr,
            )
            print(f"    expected: {expected}", file=sys.stderr)
            print(f"    got:      {produced}", file=sys.stderr)
            break
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
