"""The matching rules are public behavior, so the document stating them is guarded.

Determinism means a caller can snapshot a report. That makes the overlap and
ordering rules something they are entitled to read rather than reverse-engineer
from the scan — and something that must not quietly drift away from the code.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RULES_DOC = REPO_ROOT / "docs" / "matching-rules.md"


@pytest.fixture
def rules() -> str:
    return RULES_DOC.read_text(encoding="utf-8")


def test_the_matching_rules_are_written_down() -> None:
    assert RULES_DOC.is_file()


def test_the_tiebreaks_are_stated_in_the_order_the_resolver_applies_them(
    rules: str,
) -> None:
    """A tiebreak listed out of order is worse than one not listed at all."""
    overlap_section = rules.split("## 6.")[1].split("## 7.")[0]
    positions = [
        overlap_section.index("longest span"),
        overlap_section.index("score tier"),
        overlap_section.index("earliest start"),
        overlap_section.index("canonical ID"),
    ]

    assert positions == sorted(positions)


@pytest.mark.parametrize(
    "topic",
    ["Arabic", "diacritic", "offset", "preferred", "alternate", "determinis"],
)
def test_the_document_covers_every_observable_part_of_matching(
    rules: str, topic: str
) -> None:
    assert topic in rules


def test_the_document_is_discoverable_from_the_readme() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "docs/matching-rules.md" in readme
