"""The matching rules are public behavior, so the document stating them is guarded.

Determinism means a caller can snapshot a report. That makes the overlap and
ordering rules something they are entitled to read rather than reverse-engineer
from the scan — and something that must not quietly drift away from the code.
"""

import pytest

from conftest import REPO_ROOT

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
    [
        "Arabic",
        "diacritic",
        "offset",
        "preferred",
        "alternate",
        "determinis",
        "fuzzy",
        "correction",
        "swapped",
        "transposition",
    ],
)
def test_the_document_covers_every_observable_part_of_matching(
    rules: str, topic: str
) -> None:
    assert topic in rules


def test_the_fuzzy_pass_and_its_budget_table_are_documented(rules: str) -> None:
    section = rules.split("## 8.")[1]

    assert "uncovered" in section  # fuzzy only examines what exact left behind
    assert "Edit budget" in section  # the table's own header
    assert "|" in section  # published as a table, not prose
    assert "exact match only" in section
    assert "1 edit" in section
    assert "2 edits" in section
    assert "transposition" in section
    assert "similar enough" in section  # threshold on top of the budget


def test_the_fuzzy_ranking_tiebreaks_are_listed_in_applied_order(rules: str) -> None:
    ranking = rules.split("### Ranking")[1].split("###")[0]
    positions = [
        ranking.index("similarity"),
        ranking.index("edit distance"),
        ranking.index("score tier"),
        ranking.index("earliest start"),
    ]

    assert positions == sorted(positions)


def test_the_fuzzy_keyword_precedence_and_non_goals_are_documented(rules: str) -> None:
    section = rules.split("## 8.")[1]

    assert "fuzzy=False" in section
    assert "semver" in section  # the pass is public, semver-governed behavior
    assert "outranks" in section  # exact beats an overlapping fuzzy hit
    assert "phonetic" in section  # a stated non-goal, not a shipped feature
    assert "semantic" in section


def test_the_document_is_discoverable_from_the_readme() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "docs/matching-rules.md" in readme


@pytest.fixture
def fallback(rules: str) -> str:
    """The locale-fallback section (§5), isolated from its neighbours."""
    return rules.split("## 5.")[1].split("## 6.")[0]


@pytest.mark.parametrize(
    "topic",
    [
        "fallback chain",  # the mechanism has a name
        "built once",  # resolved at initialization, not per call
        "first locale with any match",  # the load-bearing precedence rule
        "one locale",  # every match in a report comes from one locale
        "matched_locale",  # the report names which locale answered
        "opaque identifiers",  # tags compared as written
        "language detection",  # named as a non-goal
        "fallback_chain",  # the explicit-override keyword
        "ValidationError",  # how a bad explicit chain is rejected
    ],
)
def test_the_locale_fallback_policy_is_documented(fallback: str, topic: str) -> None:
    assert topic in fallback


def test_the_default_chain_policy_is_published_as_an_ordered_list(
    fallback: str,
) -> None:
    positions = [
        fallback.index("exact locale"),
        fallback.index("same-language variants"),
        fallback.index("declared `defaultLocale`"),
    ]

    assert positions == sorted(positions)


def test_an_explicit_chain_is_documented_as_replacing_the_default(
    fallback: str,
) -> None:
    assert "replaces" in fallback  # replaces, not extends
    assert "at construction" in fallback  # validated at initialization


def test_the_composition_with_typo_tolerance_is_documented(fallback: str) -> None:
    composition = fallback.split("### Fallback composes")[1]

    assert "fuzzy" in composition
    assert "beats an exact match" in composition  # earlier fuzzy beats later exact


def test_the_fallback_section_states_it_is_semver_governed(fallback: str) -> None:
    assert "semver" in fallback
