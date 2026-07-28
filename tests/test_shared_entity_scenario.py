"""Several terms, one entity — the founding case, through the public API.

A German media company's users type "film", "filme", "serie" and "serien", and
every one of those is, to the backend, the same `product`. What separates them is
not which entity to query but how to narrow it. This is the scenario that shape
exists for, asserted the way an integrating developer would meet it: build a
resolver from a document, resolve a prompt, read the report.
"""

import pytest

from conftest import REPO_ROOT, lexicon_document
from lexiqr import EntityResolver, ScoreTier

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
