"""Which hit survives when two surface forms claim the same text, and in what order.

These rules are not implementation detail. A caller who caches or snapshots a
report is relying on them, so every one of them is asserted through the public
API rather than left to whatever the scan happened to emit first.
"""

from typing import Any

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


def test_a_multi_word_label_is_not_shredded_into_the_labels_inside_it() -> None:
    resolver = EntityResolver.from_dict(
        lexicon(
            "en-GB",
            ticket={"preferred": {"singular": "ticket"}},
            escalation={"preferred": {"singular": "support ticket"}},
        )
    )

    report = resolver.transform("open a support ticket now", "en-GB")

    assert [(m.canonical_id, m.span) for m in report.matches] == [
        ("escalation", (7, 21))
    ]


def test_equal_length_overlaps_are_broken_by_tier() -> None:
    """Two five-character forms straddle "bb", so length cannot separate them.

    The later form is the better-placed one by position, and still loses:
    tier is asked before start.
    """
    resolver = EntityResolver.from_dict(
        lexicon(
            "en-GB",
            product={"preferred": {"singular": "bb cc"}},
            invoice={"preferred": {"singular": "zz"}, "alternates": ["aa bb"]},
        )
    )

    report = resolver.transform("aa bb cc", "en-GB")

    assert [(m.canonical_id, m.score_tier, m.span) for m in report.matches] == [
        ("product", ScoreTier.PREFERRED, (3, 8))
    ]


def test_an_equal_length_equal_tier_overlap_is_broken_by_the_earlier_start() -> None:
    resolver = EntityResolver.from_dict(
        lexicon(
            "en-GB",
            product={"preferred": {"singular": "aa bb"}},
            invoice={"preferred": {"singular": "bb cc"}},
        )
    )

    report = resolver.transform("aa bb cc", "en-GB")

    assert [(m.canonical_id, m.span) for m in report.matches] == [("product", (0, 5))]


def test_forms_that_differ_only_by_accent_are_separated_the_same_way_every_time() -> (
    None
):
    """Two entities may claim forms the load-time ambiguity check cannot see.

    That check compares casefolded text; "épisode" and "episode" survive it and
    then collide at the same span once folded. Nothing about the text can
    choose between them, so the canonical ID does — identically, every run.
    """
    resolver = EntityResolver.from_dict(
        lexicon(
            "fr-FR",
            zebre={"preferred": {"singular": "épisode"}},
            alpaga={"preferred": {"singular": "episode"}},
        )
    )

    reports = [resolver.transform("un episode", "fr-FR") for _ in range(5)]

    assert {tuple(report.matches) for report in reports} == {tuple(reports[0].matches)}
    assert [m.canonical_id for m in reports[0].matches] == ["alpaga"]


def test_hits_that_do_not_overlap_are_all_kept() -> None:
    resolver = EntityResolver.from_dict(
        lexicon(
            "en-GB",
            ticket={"preferred": {"singular": "ticket"}},
            product={"preferred": {"singular": "widget"}},
        )
    )

    report = resolver.transform("a ticket about a widget", "en-GB")

    assert [m.canonical_id for m in report.matches] == ["ticket", "product"]


def test_the_report_is_ordered_by_position_not_by_tier() -> None:
    """A canonical-tier hit early in the prompt still comes first."""
    resolver = EntityResolver.from_dict(
        lexicon(
            "en-GB",
            product={"preferred": {"singular": "widget"}},
            invoice={"preferred": {"singular": "bill"}},
        )
    )

    report = resolver.transform("count invoice rows against each widget", "en-GB")

    assert [(m.score_tier, m.span) for m in report.matches] == [
        (ScoreTier.CANONICAL, (6, 13)),
        (ScoreTier.PREFERRED, (32, 38)),
    ]


def test_an_exact_hit_outranks_an_overlapping_fuzzy_hit_even_a_longer_one() -> None:
    """The one new dimension: kind is asked before span length.

    A correctly spelled word must never be displaced by a fuzzy guess, so where
    the two kinds claim overlapping text the exact hit wins outright — even when
    the fuzzy hit spans more of the prompt.
    """
    from lexiqr.overlaps import Candidate, resolve

    exact = Candidate("product", "widget", (4, 10), ScoreTier.CANONICAL, is_fuzzy=False)
    longer_fuzzy = Candidate(
        "gadget", "gadgetry", (0, 12), ScoreTier.PREFERRED, is_fuzzy=True
    )

    assert resolve((longer_fuzzy, exact)) == (exact,)


def test_a_correctly_spelled_and_a_misspelled_term_both_resolve() -> None:
    resolver = EntityResolver.from_dict(
        lexicon("en-GB", product={"preferred": {"singular": "widget"}})
    )

    report = resolver.transform("a widget beside a widgt", "en-GB")

    kinds = [(m.canonical_id, m.correction) for m in report.matches]
    assert kinds == [("product", None), ("product", "widgt")]


def test_a_region_the_exact_scan_claimed_yields_no_fuzzy_candidate() -> None:
    """ "ticket" is one edit from "ticker", but the exact scan already claimed it,
    so tolerance never re-examines the word and no second, fuzzy match appears."""
    resolver = EntityResolver.from_dict(
        lexicon(
            "en-GB",
            product={"preferred": {"singular": "ticket"}},
            index={"preferred": {"singular": "ticker"}},
        )
    )

    report = resolver.transform("the ticket please", "en-GB")

    assert [(m.canonical_id, m.correction) for m in report.matches] == [
        ("product", None)
    ]


def test_a_rebuilt_resolver_reports_the_same_thing_as_the_first_one() -> None:
    """Determinism survives a rebuild of the resolver, not just a repeated call."""
    document = lexicon(
        "en-GB",
        ticket={"preferred": {"singular": "ticket"}},
        escalation={"preferred": {"singular": "support ticket"}},
        product={"preferred": {"singular": "widget", "plural": "widgets"}},
    )
    prompt = "open a support ticket about two widgets and one widget"

    reports = [
        EntityResolver.from_dict(document).transform(prompt, "en-GB") for _ in range(5)
    ]

    assert {tuple(report.matches) for report in reports} == {tuple(reports[0].matches)}
    assert [m.canonical_id for m in reports[0].matches] == [
        "escalation",
        "product",
        "product",
    ]
