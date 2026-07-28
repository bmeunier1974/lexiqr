"""The entry format's written record, guarded so it cannot drift from the code.

Three audiences read these files and none of them read the source. A lexicon
author adopts the several-terms-one-entity pattern from the authoring guide; the
next maintainer learns why the format looks like this from the ADR; an integrating
developer learns what broke from the changelog. A document that quietly stops
matching the code is worse than a missing one, because it is trusted.

So the claims that can be checked are checked: the guide's worked example is run
and its quoted output compared to what the command actually prints, and the terms
the glossary promises to define are asserted present.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import REPO_ROOT
from lexiqr.cli import EXIT_OK, main

ADR = REPO_ROOT / "docs" / "adr" / "0005-entry-metadata-format.md"
AUTHORING = REPO_ROOT / "docs" / "lexicon-authoring.md"
CONTEXT = REPO_ROOT / "CONTEXT.md"
VISION = REPO_ROOT / "VISION.md"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
MEDIEN = (
    REPO_ROOT / "schema" / "fixtures" / "valid" / "medien-shared-entity.lexicon.json"
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# --- The decision record. What was chosen matters less than what was rejected:
# --- an alternative left unrecorded is one the next person re-proposes.


def test_the_format_decisions_have_an_accepted_decision_record() -> None:
    text = read(ADR)

    assert "## Status" in text
    assert "Accepted" in text
    assert "## Context" in text
    assert "## Decision" in text
    assert "## Consequences" in text


@pytest.mark.parametrize(
    "rejected",
    [
        "magic key",  # hiding the target inside the metadata bag
        "shape union",  # nesting senses under an entity
        "null",  # no null in the value domain
        "nesting",  # no nested objects — no query language
        "second schema version",  # amend in place, pre-publication only
    ],
)
def test_the_record_names_each_rejected_alternative(rejected: str) -> None:
    assert rejected in read(ADR)


@pytest.mark.parametrize(
    "decision",
    ["canonicalId", "entry ID", "metadata", "round-trip", "pre-publication"],
)
def test_the_record_states_each_settled_decision(decision: str) -> None:
    assert decision in read(ADR)


# --- The glossary. The project's ubiquitous language: a noun the code uses and
# --- the glossary does not is a noun two people will read differently.


@pytest.mark.parametrize("noun", ["**Entry**", "**Metadata**"])
def test_the_glossary_defines_the_two_new_nouns(noun: str) -> None:
    assert noun in read(CONTEXT)


def test_the_glossary_says_several_entries_may_share_one_canonical_id() -> None:
    """Without this, "canonical ID" still reads as "the key of an entity", which
    is exactly the reading the entry model breaks."""
    canonical_id = read(CONTEXT).split("**Canonical ID**")[1].split("\n")[0]

    assert "several entries" in canonical_id.lower()


def test_the_glossary_entity_match_names_the_entry_and_the_filter() -> None:
    entity_match = read(CONTEXT).split("**Entity match**")[1].split("\n")[0]

    assert "entry" in entity_match.lower()
    assert "metadata" in entity_match.lower()


# --- The vision. Its non-goal on filter building and this feature have to read
# --- as one position, not two that contradict each other.


def test_the_vision_carries_a_capability_for_entry_metadata() -> None:
    capabilities = read(VISION).split("## Capabilities")[1].split("## Non-goals")[0]

    assert "metadata" in capabilities.lower()
    assert "canonical" in capabilities.lower()


def test_the_vision_non_goal_says_lexiqr_carries_filters_but_never_builds_them() -> (
    None
):
    non_goals = read(VISION).split("## Non-goals")[1].split("## Constraints")[0]
    filter_building = next(
        line for line in non_goals.split("\n") if "filter building" in line.lower()
    )

    assert "carries" in filter_building.lower()
    assert "never" in filter_building.lower()


# --- The authoring guide. Its worked example is the thing an author copies, so
# --- what it claims the CLI prints is compared to what the CLI prints.


@pytest.mark.parametrize(
    "topic",
    [
        "canonicalId",  # the field itself
        "movie",  # the worked example
        "series",
        "productType",  # a filter in the example
        "never interprets",  # the carry-only position
    ],
)
def test_the_guide_works_the_several_terms_one_entity_pattern_through(
    topic: str,
) -> None:
    assert topic in read(AUTHORING)


def test_the_guide_states_what_a_filter_value_may_hold() -> None:
    guide = read(AUTHORING)

    assert "boolean" in guide.lower()
    assert (
        "list of strings" in guide.lower() or "list of unique strings" in guide.lower()
    )


def test_the_output_the_guide_quotes_is_the_output_the_command_prints(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The guide tells an author what they will see; this is that promise, run.

    An author who sees different text than the page shows stops trusting the page,
    and the two lines this feature added are exactly the ones they are looking for.
    """
    code = main(["try", str(MEDIEN), "--locale", "de-DE", "wo sind die filme"])
    printed = capsys.readouterr().out

    assert code == EXIT_OK
    guide = read(AUTHORING)
    for line in printed.splitlines():
        if line.strip().startswith(("entry:", "filter:")):
            assert line.strip() in guide


# --- The changelog. A breaking change an integrating developer discovers by
# --- upgrading is a breaking change that was not recorded.


def test_the_changelog_records_the_feature_under_unreleased() -> None:
    unreleased = read(CHANGELOG).split("## [Unreleased]")[1].split("## [1.0.0]")[0]

    assert "metadata" in unreleased.lower()
    assert "canonicalId" in unreleased


@pytest.mark.parametrize(
    "breaking",
    ["entry_id", "serialize_report", "identifier"],
)
def test_the_changelog_calls_out_each_breaking_change(breaking: str) -> None:
    unreleased = read(CHANGELOG).split("## [Unreleased]")[1].split("## [1.0.0]")[0]
    changed = unreleased.lower()

    assert "breaking" in changed
    assert breaking.lower() in changed
