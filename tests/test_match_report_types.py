"""The completed shape of the match report (ADR 0002).

Plans 004 and 005 populate `correction` and vary `matched_locale`; neither may
*add* a field, because consumers construct and pattern-match these types and a
new field is a breaking change. So the full field set lands here, and the ones
this epic can already answer are mandatory rather than optional.
"""

from pathlib import Path

import pytest

from lexiqr import EntityMatch, EntityResolver, ScoreTier

ACME = (
    Path(__file__).resolve().parent.parent
    / "schema"
    / "fixtures"
    / "valid"
    / "acme-multilingual.lexicon.json"
)


@pytest.fixture
def acme() -> EntityResolver:
    return EntityResolver.from_file(ACME)


def test_a_match_cannot_be_built_without_saying_which_tier_it_scored_in() -> None:
    with pytest.raises(TypeError):
        EntityMatch(  # type: ignore[call-arg]
            canonical_id="product",
            surface_form="flooff",
            span=(7, 13),
            matched_locale="de-DE",
        )


def test_a_match_cannot_be_built_without_saying_which_locale_matched() -> None:
    with pytest.raises(TypeError):
        EntityMatch(  # type: ignore[call-arg]
            canonical_id="product",
            surface_form="flooff",
            span=(7, 13),
            score_tier=ScoreTier.PREFERRED,
        )


@pytest.mark.parametrize(
    ("prompt", "locale"),
    [
        ("wo ist flooff", "de-DE"),
        ("where is the widget", "en-GB"),
        ("die rechnung bitte", "de-DE"),
        ("open a ticket", "en-GB"),
    ],
)
def test_every_match_transform_emits_names_a_tier_and_the_locale_it_was_read_in(
    acme: EntityResolver, prompt: str, locale: str
) -> None:
    report = acme.transform(prompt, locale)

    assert report.matches
    for match in report.matches:
        assert isinstance(match.score_tier, ScoreTier)
        assert match.matched_locale == locale


def test_nothing_populates_a_correction_until_the_fuzzy_pass_lands(
    acme: EntityResolver,
) -> None:
    report = acme.transform("wo ist flooff", "de-DE")

    assert report.matches
    assert all(match.correction is None for match in report.matches)


def test_a_locale_the_lexicon_never_declares_reports_no_matches_rather_than_raising(
    acme: EntityResolver,
) -> None:
    report = acme.transform("ou est le produit", "fr-FR")

    assert report.matches == ()
    assert report.locale == "fr-FR"


def test_an_empty_prompt_reports_no_matches_rather_than_raising(
    acme: EntityResolver,
) -> None:
    report = acme.transform("", "de-DE")

    assert report.matches == ()
    assert report.prompt == ""
