"""The public resolution API: constructing an EntityResolver and calling transform."""

import json
from pathlib import Path
from typing import Any

import pytest

from lexiqr import EntityResolver

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "examples" / "flooff.lexicon.json"
)


@pytest.fixture
def lexicon() -> Any:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_transform_echoes_the_original_prompt_and_the_resolved_locale() -> None:
    resolver = EntityResolver.from_file(FIXTURE_PATH)

    report = resolver.transform("wo ist flooff", "de-DE")

    assert report.prompt == "wo ist flooff"
    assert report.locale == "de-DE"


def test_a_resolver_built_from_a_dict_behaves_like_one_built_from_the_file(
    lexicon: Any,
) -> None:
    from_dict = EntityResolver.from_dict(lexicon)
    from_file = EntityResolver.from_file(FIXTURE_PATH)

    assert from_dict.transform("wo ist flooff", "de-DE") == from_file.transform(
        "wo ist flooff", "de-DE"
    )


def test_a_prompt_with_no_lexicon_hits_reports_no_matches_rather_than_raising() -> None:
    resolver = EntityResolver.from_file(FIXTURE_PATH)

    report = resolver.transform("wo ist der bahnhof", "de-DE")

    assert report.matches == ()


def test_a_match_report_is_frozen_so_callers_cannot_rewrite_a_result() -> None:
    report = EntityResolver.from_file(FIXTURE_PATH).transform("wo ist flooff", "de-DE")

    with pytest.raises(AttributeError):
        report.prompt = "tampered"  # type: ignore[misc]


def test_an_entity_match_carries_the_full_field_set_with_deferred_defaults() -> None:
    from lexiqr import EntityMatch

    match = EntityMatch(canonical_id="product", surface_form="flooff", span=(8, 14))

    assert match.score_tier is None
    assert match.correction is None
    assert match.matched_locale is None
