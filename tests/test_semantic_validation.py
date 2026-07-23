"""Checks core enforces that the published schema cannot express.

ADR 0003 licenses exactly one kind of divergence: core may be *stricter* than
the schema, provided every such check is documented. These fixtures are the
divergence — each one passes the published schema and is still rejected — and
docs/lexicon-semantic-checks.md is the document that licenses them.
"""

import json
from pathlib import Path

import pytest

from lexiqr import EntityResolver, ValidationError

REPO_ROOT = Path(__file__).resolve().parent.parent
SEMANTIC_CORPUS = REPO_ROOT / "schema" / "fixtures" / "semantic"


def load(name: str) -> dict[str, object]:
    document = json.loads(
        (SEMANTIC_CORPUS / f"{name}.lexicon.json").read_text(encoding="utf-8")
    )
    assert isinstance(document, dict)
    return document


def test_two_entities_claiming_the_same_surface_form_in_a_locale_are_rejected() -> None:
    """An ambiguous lexicon has no deterministic resolution, and determinism
    is a headline guarantee — so the ambiguity is refused at the door."""
    with pytest.raises(ValidationError) as raised:
        EntityResolver.from_dict(load("duplicate-surface-form-across-entities"))

    error = raised.value
    assert error.locale == "de-DE"
    message = str(error)
    assert "flooff" in message
    assert "product" in message
    assert "invoice" in message


def test_one_entity_declaring_the_same_surface_form_twice_is_rejected() -> None:
    """The stated decision: rejected, not quietly de-duplicated.

    An alternate that repeats the preferred singular would otherwise produce
    two matches over the same span at two different score tiers — so it is a
    lexicon bug, and saying so beats silently picking one.
    """
    with pytest.raises(ValidationError) as raised:
        EntityResolver.from_dict(load("duplicate-surface-form-within-one-entity"))

    error = raised.value
    assert error.canonical_id == "product"
    assert error.locale == "de-DE"
    assert error.field == "alternates[1]"


def test_a_surface_form_that_is_only_whitespace_is_rejected() -> None:
    """The schema's minLength cannot tell a label from a blank one."""
    with pytest.raises(ValidationError) as raised:
        EntityResolver.from_dict(load("blank-surface-form"))

    error = raised.value
    assert error.canonical_id == "product"
    assert error.locale == "de-DE"
    assert error.field == "alternates[0]"


def semantic_fixtures() -> list[Path]:
    return sorted(SEMANTIC_CORPUS.glob("*.lexicon.json"))


@pytest.mark.parametrize("fixture", semantic_fixtures(), ids=lambda p: p.stem)
def test_every_semantic_fixture_passes_the_schema_and_is_rejected_by_core(
    fixture: Path,
) -> None:
    """This is what makes a fixture semantic rather than structural.

    A fixture in this directory that the schema *also* rejects is misfiled —
    it proves nothing about the divergence ADR 0003 licenses.
    """
    from jsonschema import Draft202012Validator

    schema = json.loads(
        (REPO_ROOT / "schema" / "lexicon.v1.schema.json").read_text(encoding="utf-8")
    )
    document = json.loads(fixture.read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(document)

    with pytest.raises(ValidationError):
        EntityResolver.from_dict(document)


@pytest.mark.parametrize("fixture", semantic_fixtures(), ids=lambda p: p.stem)
def test_every_semantic_fixture_is_licensed_by_the_divergence_document(
    fixture: Path,
) -> None:
    """ADR 0003 permits core to be stricter only where it says so in writing.

    An undocumented check is drift, however well-intentioned — so the document
    must name every fixture in this directory.
    """
    document = (REPO_ROOT / "docs" / "lexicon-semantic-checks.md").read_text(
        encoding="utf-8"
    )

    assert fixture.name in document
