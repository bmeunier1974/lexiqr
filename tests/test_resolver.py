"""The public resolution API: constructing an EntityResolver and calling transform."""

from typing import Any

import pytest

from conftest import FLOOFF_LEXICON, flooff_document
from lexiqr import EntityResolver


@pytest.fixture
def lexicon() -> Any:
    return flooff_document()


def test_transform_echoes_the_original_prompt_and_the_resolved_locale() -> None:
    resolver = EntityResolver.from_file(FLOOFF_LEXICON)

    report = resolver.transform("wo ist flooff", "de-DE")

    assert report.prompt == "wo ist flooff"
    assert report.locale == "de-DE"


def test_flooff_resolves_to_the_product_entity_at_its_span_in_the_prompt() -> None:
    resolver = EntityResolver.from_file(FLOOFF_LEXICON)

    report = resolver.transform("wo ist flooff", "de-DE")

    assert len(report.matches) == 1
    match = report.matches[0]
    assert match.canonical_id == "product"
    assert match.surface_form == "flooff"
    assert match.span == (7, 13)
    assert "wo ist flooff"[match.span[0] : match.span[1]] == "flooff"


def test_a_misspelled_surface_form_still_resolves_carrying_its_correction() -> None:
    resolver = EntityResolver.from_file(FLOOFF_LEXICON)

    report = resolver.transform("wo ist floof", "de-DE")

    assert len(report.matches) == 1
    match = report.matches[0]
    assert match.canonical_id == "product"
    assert match.surface_form == "flooff"
    assert match.correction == "floof"
    assert report.prompt[match.span[0] : match.span[1]] == "floof"


def test_a_hit_on_a_preferred_surface_form_scores_in_the_preferred_tier() -> None:
    from lexiqr import ScoreTier

    report = EntityResolver.from_file(FLOOFF_LEXICON).transform(
        "wo ist flooff", "de-DE"
    )

    assert report.matches[0].score_tier is ScoreTier.PREFERRED
    assert report.matches[0].matched_locale == "de-DE"


def test_a_resolver_built_from_a_dict_behaves_like_one_built_from_the_file(
    lexicon: Any,
) -> None:
    from_dict = EntityResolver.from_dict(lexicon)
    from_file = EntityResolver.from_file(FLOOFF_LEXICON)

    assert from_dict.transform("wo ist flooff", "de-DE") == from_file.transform(
        "wo ist flooff", "de-DE"
    )


def test_a_prompt_with_no_lexicon_hits_reports_no_matches_rather_than_raising() -> None:
    resolver = EntityResolver.from_file(FLOOFF_LEXICON)

    report = resolver.transform("wo ist der bahnhof", "de-DE")

    assert report.matches == ()


def test_a_match_report_is_frozen_so_callers_cannot_rewrite_a_result() -> None:
    report = EntityResolver.from_file(FLOOFF_LEXICON).transform(
        "wo ist flooff", "de-DE"
    )

    with pytest.raises(AttributeError):
        report.prompt = "tampered"  # type: ignore[misc]


def test_an_entity_match_carries_the_full_field_set_with_correction_deferred() -> None:
    from lexiqr import EntityMatch, ScoreTier

    match = EntityMatch(
        canonical_id="product",
        entry_id="product",
        surface_form="flooff",
        span=(8, 14),
        score_tier=ScoreTier.PREFERRED,
        matched_locale="de-DE",
    )

    assert match.score_tier is ScoreTier.PREFERRED
    assert match.matched_locale == "de-DE"
    assert match.correction is None
    # Absent is empty, and the entry is a real string rather than an absence.
    assert match.metadata == {}
    assert match.entry_id == "product"
