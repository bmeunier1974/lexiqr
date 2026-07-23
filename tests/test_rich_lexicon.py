"""Loading a lexicon that carries a real tenant's jargon, not the flooff toy.

Several entities, several locales, preferred plurals and alternate labels —
asserted through the public API, so what these tests pin down is what an
integrating developer can actually observe.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from lexiqr import EntityResolver

REPO_ROOT = Path(__file__).resolve().parent.parent
ACME = REPO_ROOT / "schema" / "fixtures" / "valid" / "acme-multilingual.lexicon.json"


def acme_document() -> Any:
    return json.loads(ACME.read_text(encoding="utf-8"))


@pytest.fixture
def acme() -> EntityResolver:
    return EntityResolver.from_file(ACME)


@pytest.mark.parametrize(
    ("prompt", "locale", "canonical_id"),
    [
        ("wo ist flooff", "de-DE", "product"),
        ("where is the widget", "en-GB", "product"),
        ("أين منتج", "ar-EG", "product"),
        ("die rechnung bitte", "de-DE", "invoice"),
        ("send the invoice", "en-GB", "invoice"),
        ("open a ticket", "en-GB", "support-ticket"),
    ],
)
def test_every_entity_resolves_in_every_locale_it_declares(
    acme: EntityResolver, prompt: str, locale: str, canonical_id: str
) -> None:
    report = acme.transform(prompt, locale)

    assert [match.canonical_id for match in report.matches] == [canonical_id]


@pytest.mark.parametrize(
    ("prompt", "surface_form"),
    [
        ("wo ist flooff", "flooff"),
        ("wo sind die flooffs", "flooffs"),
        ("wo ist der artikel", "artikel"),
        ("wo ist die ware", "ware"),
    ],
)
def test_preferred_singular_plural_and_every_alternate_all_resolve(
    acme: EntityResolver, prompt: str, surface_form: str
) -> None:
    report = acme.transform(prompt, "de-DE")

    assert [(m.canonical_id, m.surface_form) for m in report.matches] == [
        ("product", surface_form)
    ]


def test_an_entity_declaring_no_plural_and_no_alternates_still_loads(
    acme: EntityResolver,
) -> None:
    report = acme.transform("open a ticket", "en-GB")

    assert [match.canonical_id for match in report.matches] == ["support-ticket"]


@pytest.mark.parametrize(
    ("prompt", "locale"),
    [
        ("wo sind die flooffs und die rechnungen", "de-DE"),
        ("the widgets, the bill and a ticket", "en-GB"),
        ("أين منتجات", "ar-EG"),
    ],
)
def test_a_lexicon_read_from_a_file_and_one_handed_over_as_a_dict_agree(
    prompt: str, locale: str
) -> None:
    """A tenant lexicon sourced from a database must behave as one on disk."""
    from_file = EntityResolver.from_file(ACME)
    from_dict = EntityResolver.from_dict(acme_document())

    assert from_file.transform(prompt, locale) == from_dict.transform(prompt, locale)


def test_the_fixture_exercises_every_part_of_the_format_this_story_claims() -> None:
    """Guards the fixture itself: a thinned-out corpus would hollow these tests."""
    document = acme_document()
    entities = document["entities"]
    locales = {locale for entity in entities.values() for locale in entity["locales"]}
    forms = [
        surface_forms
        for entity in entities.values()
        for surface_forms in entity["locales"].values()
    ]

    assert len(entities) >= 3
    assert len(locales) >= 3
    assert any(not locale.startswith(("de", "en")) for locale in locales)
    assert any("plural" in form["preferred"] for form in forms)
    assert any(form.get("alternates") for form in forms)
    assert any("plural" not in form["preferred"] for form in forms)
