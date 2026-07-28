"""What core accepts and rejects when a lexicon is loaded.

Validation happens at `EntityResolver` construction, never at `transform()`
time: an integrating developer's misconfiguration must surface at startup, not
in production traffic.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from conftest import flooff_document, lexicon_document
from lexiqr import (
    MAX_SURFACE_FORM_LENGTH,
    EntityResolver,
    Lexicon,
    ValidationError,
)


def with_alternate(alternate: str) -> Any:
    """The flooff lexicon with one extra alternate label for `product`."""
    document = flooff_document()
    document["entities"]["product"]["locales"]["de-DE"]["alternates"] = [alternate]
    return document


def authored_in(tag: str) -> dict[str, Any]:
    """A one-entity lexicon whose only locale key is `tag`."""
    return lexicon_document(
        tag, default_locale="de-DE", product={"preferred": {"singular": "flooff"}}
    )


def test_a_lexicon_declaring_an_unsupported_schema_version_is_rejected() -> None:
    document = flooff_document()
    document["schemaVersion"] = "99"

    with pytest.raises(ValidationError) as raised:
        EntityResolver.from_dict(document)

    message = str(raised.value)
    assert "99" in message
    assert "1" in message


def test_a_lexicon_with_no_schema_version_at_all_is_rejected_the_same_way() -> None:
    document = flooff_document()
    del document["schemaVersion"]

    with pytest.raises(ValidationError):
        EntityResolver.from_dict(document)


def test_the_version_check_precedes_any_other_reading_of_the_document() -> None:
    """A document core cannot interpret is reported as such, not as a crash.

    Core has no idea what a future format's entities look like, so it must not
    try to read them before deciding it understands the version at all.
    """
    unreadable = {"schemaVersion": "99", "entities": "not what v1 means by this"}

    with pytest.raises(ValidationError) as raised:
        EntityResolver.from_dict(unreadable)

    assert raised.value.field == "schemaVersion"


def test_a_lexicon_file_is_validated_when_the_resolver_is_built(
    tmp_path: Path,
) -> None:
    document = flooff_document()
    document["schemaVersion"] = "99"
    path = tmp_path / "future.lexicon.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValidationError):
        EntityResolver.from_file(path)


def test_no_invalid_lexicon_survives_construction_to_reach_transform() -> None:
    """Misconfiguration surfaces at startup, never in production traffic."""
    document = flooff_document()
    document["schemaVersion"] = "99"

    try:
        resolver = EntityResolver.from_dict(document)
    except ValidationError:
        return

    pytest.fail(
        "construction accepted an invalid lexicon; "
        f"the failure would have been deferred to transform(): "
        f"{resolver.transform('wo ist flooff', 'de-DE')}"
    )


# --- The locale tag grammar: the BCP 47 subset the format accepts, mirroring
# --- the published schema's `$defs/locale`. A tag is an opaque identifier — it
# --- is compared case-insensitively but never rewritten — so what the grammar
# --- accepts is exactly what the schema states: an underscore is not a hyphen,
# --- and a tag is never canonicalised into shape on the author's behalf.


@pytest.mark.parametrize(
    "tag", ["de", "de-DE", "DE-de", "de-Latn-DE", "es-419", "fil-PH"]
)
def test_a_well_formed_locale_tag_is_accepted_in_the_casing_it_was_authored_in(
    tag: str,
) -> None:
    lexicon = Lexicon.from_dict(authored_in(tag))

    assert set(lexicon.entries["product"].locales) == {tag}


@pytest.mark.parametrize(
    "tag", ["", "d", "de_DE", "german!", "deutsch-DE", "de-DE-x", "de-DEU"]
)
def test_a_locale_tag_outside_the_grammar_is_rejected_and_named(tag: str) -> None:
    with pytest.raises(ValidationError) as raised:
        Lexicon.from_dict(authored_in(tag))

    error = raised.value
    assert error.canonical_id == "product"
    assert error.locale == tag
    assert error.field == "locales"


def test_the_declared_default_obeys_the_same_grammar_as_a_locale_key() -> None:
    document = authored_in("de-DE")
    document["defaultLocale"] = "de_DE"

    with pytest.raises(ValidationError) as raised:
        Lexicon.from_dict(document)

    assert raised.value.field == "defaultLocale"


# --- The surface-form length limit, at its boundary. The limit is a public
# --- constant, so these read against the number lexiqr actually enforces rather
# --- than a copy of it that could drift.


def test_a_surface_form_at_the_maximum_length_is_accepted() -> None:
    longest = "f" * MAX_SURFACE_FORM_LENGTH

    lexicon = Lexicon.from_dict(with_alternate(longest))

    assert lexicon.entries["product"].locales["de-DE"].alternates == (longest,)


def test_a_surface_form_one_character_over_the_maximum_is_rejected() -> None:
    with pytest.raises(ValidationError) as raised:
        Lexicon.from_dict(with_alternate("f" * (MAX_SURFACE_FORM_LENGTH + 1)))

    error = raised.value
    assert error.canonical_id == "product"
    assert error.locale == "de-DE"
    assert error.field == "alternates[0]"
    assert str(MAX_SURFACE_FORM_LENGTH) in error.message
