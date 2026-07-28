"""Several terms, one entity — the founding case, through the public API.

A German media company's users type "film", "filme", "serie" and "serien", and
every one of those is, to the backend, the same `product`. What separates them is
not which entity to query but how to narrow it. This is the scenario that shape
exists for, asserted the way an integrating developer would meet it: build a
resolver from a document, resolve a prompt, read the report.
"""

import json

import pytest

from conftest import FLOOFF_LEXICON, REPO_ROOT, lexicon_document
from lexiqr import EntityResolver, MatchReport, ScoreTier

#: The shape as a lexicon author would ship it, so the corpus carries a worked
#: example and the ADR 0003 equivalence harness covers it: a document using the
#: feature must pass the published schema *and* load in core.
MEDIEN = (
    REPO_ROOT / "schema" / "fixtures" / "valid" / "medien-shared-entity.lexicon.json"
)


def test_two_entries_resolving_to_one_entity_both_report_that_entity() -> None:
    """The point of the entry model: no invented entities the backend lacks.

    "movie" and "series" are entries — the tenant's vocabulary. `product` is the
    entity. A consuming service reads one canonical ID it can actually query,
    and the surface form still names the word the user typed.
    """
    resolver = EntityResolver.from_dict(
        lexicon_document(
            "en-US",
            movie={
                "canonicalId": "product",
                "locales": {
                    "en-US": {"preferred": {"singular": "movie", "plural": "movies"}}
                },
            },
            series={
                "canonicalId": "product",
                "locales": {"en-US": {"preferred": {"singular": "series"}}},
            },
        )
    )

    report = resolver.transform("show me movies", "en-US")

    assert [
        (match.canonical_id, match.surface_form, match.score_tier)
        for match in report.matches
    ] == [("product", "movies", ScoreTier.PREFERRED)]


def _medien_resolver() -> EntityResolver:
    """Two entries whose German words share no spelling with either identifier."""
    return EntityResolver.from_dict(
        lexicon_document(
            "de-DE",
            movie={
                "canonicalId": "product",
                "locales": {
                    "de-DE": {"preferred": {"singular": "film", "plural": "filme"}}
                },
            },
            series={
                "canonicalId": "product",
                "locales": {
                    "de-DE": {"preferred": {"singular": "serie", "plural": "serien"}}
                },
            },
        )
    )


def test_naming_an_entry_outright_resolves_at_the_canonical_tier() -> None:
    """The identifier of last resort is the *entry* ID, so "movie" still resolves.

    An entry's own name has always been matchable at the lowest confidence; that
    does not change because the entry now resolves somewhere else. What the match
    reports is the entity — the entry ID was only the way in.
    """
    report = _medien_resolver().transform("zeige movie an", "de-DE")

    assert [(m.canonical_id, m.surface_form, m.score_tier) for m in report.matches] == [
        ("product", "movie", ScoreTier.CANONICAL)
    ]


def test_the_shared_target_is_not_matchable_unless_an_entry_is_named_for_it() -> None:
    """ "product" is the backend's word, and no entry declares it.

    If the target were matchable, every entry sharing it would claim the same
    canonical-tier form and collide over a word the tenant never wrote — the
    lexicon would be refused for a reason internal to lexiqr.
    """
    report = _medien_resolver().transform("zeige product an", "de-DE")

    assert report.matches == ()


@pytest.mark.parametrize(
    ("prompt", "locale", "surface_form"),
    [
        ("wo sind die filme", "de-DE", "filme"),
        ("zeige mir den spielfilm", "de-DE", "spielfilm"),
        ("welche serien laufen", "de-DE", "serien"),
        ("show me the movies", "en-GB", "movies"),
        ("which series is on", "en-GB", "series"),
    ],
)
def test_the_published_fixture_resolves_every_entry_to_the_one_entity(
    prompt: str, locale: str, surface_form: str
) -> None:
    """Both entries, both locales, preferred and alternate forms — all `product`.

    A tenant maintains the words; the backend keeps the one entity it queries.
    """
    report = EntityResolver.from_file(MEDIEN).transform(prompt, locale)

    assert [(m.canonical_id, m.surface_form) for m in report.matches] == [
        ("product", surface_form)
    ]


def test_a_match_carries_the_filter_of_the_entry_that_answered() -> None:
    """The jargon-to-filter half of the mapping, delivered.

    Without this a consuming service knows `product` was named and has to keep its
    own per-tenant table to learn that this tenant's "filme" meant the Movie kind
    — which is the table lexiqr exists to remove.
    """
    report = EntityResolver.from_file(MEDIEN).transform("wo sind die filme", "de-DE")

    match = report.matches[0]
    assert (match.canonical_id, match.entry_id) == ("product", "movie")
    assert dict(match.metadata) == {
        "productType": "Movie",
        "genre": ("drama", "thriller"),
    }


def test_a_match_from_an_entry_with_no_filter_carries_an_empty_one() -> None:
    """Empty, never absent, so consuming code needs no guard — and the entry ID is
    a real string, equal to the canonical ID, rather than an absence to interpret."""
    report = EntityResolver.from_file(FLOOFF_LEXICON).transform(
        "wo ist flooff", "de-DE"
    )

    match = report.matches[0]
    assert (match.canonical_id, match.entry_id) == ("product", "product")
    assert match.metadata == {}


def test_a_misspelling_resolves_to_the_same_entry_and_filter_as_the_exact_word() -> (
    None
):
    """Tolerance must never silently drop the filter.

    A fuzzy hit is a hit on a declared form, so it carries what that form's entry
    carries. Asserted against the exact spelling rather than a literal, so the two
    paths cannot drift apart.
    """
    resolver = EntityResolver.from_file(MEDIEN)

    exact = resolver.transform("wo ist der spielfilm", "de-DE").matches[0]
    fuzzy = resolver.transform("wo ist der spielfim", "de-DE").matches[0]

    assert fuzzy.correction == "spielfim"
    assert (fuzzy.entry_id, fuzzy.metadata) == (exact.entry_id, exact.metadata)
    assert (fuzzy.canonical_id, fuzzy.surface_form) == (
        exact.canonical_id,
        exact.surface_form,
    )


def test_the_filter_a_caller_was_handed_cannot_be_mutated() -> None:
    """Lexicon-derived data reaches a service through a match; a service that could
    edit it in place would corrupt every later match of the same entry."""
    match = EntityResolver.from_file(MEDIEN).transform("die filme", "de-DE").matches[0]

    with pytest.raises(TypeError):
        match.metadata["productType"] = "Series"  # type: ignore[index]


def test_a_filter_changes_nothing_about_which_matches_come_back_or_their_order() -> (
    None
):
    """The stated non-goal: metadata is carried, never consulted.

    The same lexicon with every filter stripped must resolve identically in
    everything but the filters themselves — same matches, same tiers, same order.
    """
    declared = json.loads(MEDIEN.read_text(encoding="utf-8"))
    stripped = json.loads(MEDIEN.read_text(encoding="utf-8"))
    for entity in stripped["entities"].values():
        del entity["metadata"]

    prompt = "wo sind die filme und die serien und ein spielfim"
    with_filters = EntityResolver.from_dict(declared).transform(prompt, "de-DE")
    without = EntityResolver.from_dict(stripped).transform(prompt, "de-DE")

    def observable(report: MatchReport) -> list[tuple[str, str, tuple[int, int], str]]:
        return [
            (m.canonical_id, m.entry_id, m.span, m.score_tier.value)
            for m in report.matches
        ]

    assert observable(with_filters) == observable(without)
    assert [dict(m.metadata) for m in without.matches] == [{}, {}, {}]
