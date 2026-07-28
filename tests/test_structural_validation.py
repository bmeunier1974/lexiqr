"""Rejecting a structurally invalid lexicon, precisely enough to act on.

An integrating developer who catches one of these must be able to tell the
lexicon's owner exactly where to look, without ever reading lexiqr's source.
So every test asserts the three coordinates the error carries — canonical ID,
locale, field — and that the message names them in prose. Asserting only the
exception type would let that precision rot unnoticed.

Everything here is *structural*: a fault the published JSON Schema also
catches. Checks that go beyond what the schema can express live elsewhere.
"""

import json
from pathlib import Path

import pytest

from conftest import REPO_ROOT
from lexiqr import EntityResolver, ValidationError

INVALID_CORPUS = REPO_ROOT / "schema" / "fixtures" / "invalid"


def load(name: str) -> dict[str, object]:
    document = json.loads(
        (INVALID_CORPUS / f"{name}.lexicon.json").read_text(encoding="utf-8")
    )
    assert isinstance(document, dict)
    return document


def test_a_locale_missing_its_preferred_singular_names_entity_locale_and_field() -> (
    None
):
    with pytest.raises(ValidationError) as raised:
        EntityResolver.from_dict(load("missing-preferred-singular"))

    error = raised.value
    assert error.canonical_id == "product"
    assert error.locale == "de-DE"
    assert error.field == "preferred.singular"


def test_the_message_names_the_coordinates_so_it_can_be_pasted_into_a_ticket() -> None:
    with pytest.raises(ValidationError) as raised:
        EntityResolver.from_dict(load("missing-preferred-singular"))

    message = str(raised.value)
    assert "product" in message
    assert "de-DE" in message
    assert "preferred.singular" in message
    assert message.endswith(".")


def test_a_malformed_locale_tag_is_rejected_and_named() -> None:
    with pytest.raises(ValidationError) as raised:
        EntityResolver.from_dict(load("malformed-locale-tag"))

    error = raised.value
    assert error.canonical_id == "product"
    assert error.locale == "german!"
    assert error.field == "locales"


@pytest.mark.parametrize(
    ("fixture", "field"),
    [
        ("empty-surface-form", "preferred.singular"),
        ("empty-alternate", "alternates[1]"),
    ],
)
def test_an_empty_surface_form_is_rejected_and_named(fixture: str, field: str) -> None:
    """A surface form nobody can type is a lexicon bug, not an empty match."""
    with pytest.raises(ValidationError) as raised:
        EntityResolver.from_dict(load(fixture))

    error = raised.value
    assert error.canonical_id == "product"
    assert error.locale == "de-DE"
    assert error.field == field


@pytest.mark.parametrize(
    ("fixture", "canonical_id", "locale", "field"),
    [
        ("wrong-type-for-entities", None, None, "entities"),
        ("wrong-type-for-alternates", "product", "de-DE", "alternates"),
        ("entity-with-no-locales", "product", None, "locales"),
        ("document-with-no-entities", None, None, "entities"),
        ("missing-default-locale", None, None, "defaultLocale"),
    ],
)
def test_a_structurally_broken_document_faults_the_coordinates_it_can_name(
    fixture: str, canonical_id: str | None, locale: str | None, field: str
) -> None:
    """Coordinates a fault does not have stay None — a document-level fault
    belongs to no entity, and must not be reported as if it did."""
    with pytest.raises(ValidationError) as raised:
        EntityResolver.from_dict(load(fixture))

    error = raised.value
    assert error.canonical_id == canonical_id
    assert error.locale == locale
    assert error.field == field


def test_a_key_the_format_does_not_define_is_rejected_rather_than_ignored() -> None:
    """A silently ignored typo is a surface form the tenant believes is live."""
    with pytest.raises(ValidationError) as raised:
        EntityResolver.from_dict(load("unknown-key"))

    error = raised.value
    assert error.canonical_id == "product"
    assert error.locale == "de-DE"
    assert error.field == "synonyms"
    assert "alternates" in str(error), "the message should suggest the real key"


def test_a_file_that_is_not_valid_json_is_reported_as_a_lexicon_problem(
    tmp_path: Path,
) -> None:
    path = tmp_path / "truncated.lexicon.json"
    path.write_text('{"schemaVersion": "1",', encoding="utf-8")

    with pytest.raises(ValidationError) as raised:
        EntityResolver.from_file(path)

    assert "JSON" in str(raised.value)


def invalid_fixtures() -> list[str]:
    return sorted(
        path.name.removesuffix(".lexicon.json")
        for path in INVALID_CORPUS.glob("*.lexicon.json")
    )


@pytest.mark.parametrize("fixture", invalid_fixtures())
def test_no_invalid_fixture_escapes_as_an_unstructured_exception(
    fixture: str, tmp_path: Path
) -> None:
    """Both construction routes, every fixture: the failure is always ours.

    A KeyError or AttributeError leaking out of the loader is unactionable —
    the developer cannot tell whether their lexicon is wrong or lexiqr is.
    """
    document = load(fixture)
    path = tmp_path / f"{fixture}.lexicon.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValidationError):
        EntityResolver.from_dict(document)
    with pytest.raises(ValidationError):
        EntityResolver.from_file(path)


def test_the_invalid_corpus_covers_the_formats_structural_edges() -> None:
    """Guards the corpus: coverage that quietly shrinks would hollow the suite."""
    assert set(invalid_fixtures()) >= {
        "document-with-no-entities",
        "empty-alternate",
        "empty-surface-form",
        "entity-with-no-locales",
        "malformed-locale-tag",
        "missing-default-locale",
        "missing-preferred-singular",
        "unknown-key",
        "wrong-type-for-alternates",
        "wrong-type-for-entities",
    }
