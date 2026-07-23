"""What the scan finds, and what tier it says each hit scored in.

The scan's job is to miss nothing: every occurrence of every surface form the
stated locale declares, overlaps included and unfiltered. Choosing between
overlapping hits belongs to the resolver, not here.
"""

from typing import Any

import pytest

from lexiqr import EntityResolver, ScoreTier


def lexicon(locale: str, **entities: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": "1",
        "defaultLocale": locale,
        "entities": {
            canonical_id: {"locales": {locale: forms}}
            for canonical_id, forms in entities.items()
        },
    }


def test_naming_the_entity_itself_resolves_in_the_lowest_tier() -> None:
    resolver = EntityResolver.from_dict(
        lexicon("en-GB", product={"preferred": {"singular": "widget"}})
    )

    report = resolver.transform("how many product records", "en-GB")

    assert [match.canonical_id for match in report.matches] == ["product"]
    assert report.matches[0].surface_form == "product"
    assert report.matches[0].score_tier is ScoreTier.CANONICAL


def test_every_occurrence_is_reported_not_only_the_first() -> None:
    resolver = EntityResolver.from_dict(
        lexicon("en-GB", product={"preferred": {"singular": "widget"}})
    )

    report = resolver.transform("a widget, then another widget", "en-GB")

    assert [match.span for match in report.matches] == [(2, 8), (23, 29)]


def test_a_prompt_naming_several_entities_reports_all_of_them() -> None:
    resolver = EntityResolver.from_dict(
        lexicon(
            "en-GB",
            product={"preferred": {"singular": "widget"}},
            invoice={"preferred": {"singular": "bill"}},
        )
    )

    report = resolver.transform("the bill for that widget", "en-GB")

    assert sorted(match.canonical_id for match in report.matches) == [
        "invoice",
        "product",
    ]


@pytest.mark.parametrize(
    ("prompt", "surface_form", "tier"),
    [
        ("one widget please", "widget", ScoreTier.PREFERRED),
        ("many widgets please", "widgets", ScoreTier.PREFERRED),
        ("some gadgets please", "gadgets", ScoreTier.ALTERNATE),
        ("count the product rows", "product", ScoreTier.CANONICAL),
    ],
)
def test_each_kind_of_surface_form_scores_in_its_own_tier(
    prompt: str, surface_form: str, tier: ScoreTier
) -> None:
    resolver = EntityResolver.from_dict(
        lexicon(
            "en-GB",
            product={
                "preferred": {"singular": "widget", "plural": "widgets"},
                "alternates": ["gadgets"],
            },
        )
    )

    report = resolver.transform(prompt, "en-GB")

    assert [(m.surface_form, m.score_tier) for m in report.matches] == [
        (surface_form, tier)
    ]


def test_a_surface_form_of_another_locale_is_never_matched() -> None:
    resolver = EntityResolver.from_dict(
        {
            "schemaVersion": "1",
            "defaultLocale": "en-GB",
            "entities": {
                "product": {
                    "locales": {
                        "en-GB": {"preferred": {"singular": "widget"}},
                        "de-DE": {"preferred": {"singular": "flooff"}},
                    }
                }
            },
        }
    )

    report = resolver.transform("wo ist flooff", "en-GB")

    assert report.matches == ()


def test_a_short_surface_form_does_not_match_inside_a_longer_word() -> None:
    resolver = EntityResolver.from_dict(
        lexicon("en-GB", product={"preferred": {"singular": "bill"}})
    )

    report = resolver.transform("the billing address", "en-GB")

    assert report.matches == ()


def test_the_index_reports_a_nested_form_alongside_the_form_containing_it() -> None:
    """Raw hits are unfiltered on purpose — choosing between these is #27's job."""
    from lexiqr.index import SurfaceFormIndex
    from lexiqr.lexicon import Lexicon

    compiled = SurfaceFormIndex.build(
        Lexicon.from_dict(
            lexicon(
                "en-GB",
                ticket={"preferred": {"singular": "ticket"}},
                escalation={"preferred": {"singular": "support ticket"}},
            )
        ),
        "en-GB",
    )

    hits = compiled.scan("open a support ticket now")

    assert sorted((hit.span, hit.canonical_id) for hit in hits) == [
        ((7, 21), "escalation"),
        ((15, 21), "ticket"),
    ]
