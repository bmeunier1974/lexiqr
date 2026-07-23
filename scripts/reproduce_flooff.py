"""Reproduce the flooff match from an *installed* lexiqr; exit non-zero if it fails.

The release workflow runs this inside a clean virtualenv against the package it
just published: "it publishes" is verified by installation, not by a green
upload step (ADR 0004). Deliberately stdlib-only and import-light — it must not
depend on the repo's dev environment, only on the installed wheel.
"""

import sys
from pathlib import Path

from lexiqr import EntityResolver, ScoreTier

FIXTURE = Path(__file__).resolve().parent.parent / "examples" / "flooff.lexicon.json"


def main() -> int:
    report = EntityResolver.from_file(FIXTURE).transform("wo ist flooff", "de-DE")

    if len(report.matches) != 1:
        print(f"FAIL: expected exactly one match, got {report.matches}")
        return 1

    match = report.matches[0]
    expected = ("product", "flooff", (7, 13), ScoreTier.PREFERRED)
    actual = (match.canonical_id, match.surface_form, match.span, match.score_tier)
    if actual != expected:
        print(f"FAIL: expected {expected}, got {actual}")
        return 1

    print(f"OK: {match.canonical_id} <- {match.surface_form!r} at {match.span}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
