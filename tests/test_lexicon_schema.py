"""The published lexicon schema, checked with a standard JSON Schema validator.

This is the first row of the ADR 0003 equivalence harness: a document that
passes the published schema must later also load in core.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "lexicon.v1.schema.json"
FIXTURE_PATH = REPO_ROOT / "examples" / "flooff.lexicon.json"
VALID_CORPUS = REPO_ROOT / "schema" / "fixtures" / "valid"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def validator() -> Draft202012Validator:
    return Draft202012Validator(load(SCHEMA_PATH))


def test_flooff_fixture_lexicon_passes_the_published_schema(
    validator: Draft202012Validator,
) -> None:
    validator.validate(load(FIXTURE_PATH))


def test_every_valid_corpus_fixture_passes_the_published_schema(
    validator: Draft202012Validator,
) -> None:
    fixtures = sorted(VALID_CORPUS.glob("*.lexicon.json"))

    assert fixtures, f"no valid fixtures found in {VALID_CORPUS}"
    for fixture in fixtures:
        validator.validate(load(fixture))


def test_flooff_fixture_maps_the_surface_form_flooff_to_canonical_id_product() -> None:
    lexicon = load(FIXTURE_PATH)

    assert lexicon["defaultLocale"] == "de-DE"
    assert (
        lexicon["entities"]["product"]["locales"]["de-DE"]["preferred"]["singular"]
        == "flooff"
    )


def test_a_document_that_passes_the_schema_also_loads_in_core(
    validator: Draft202012Validator,
) -> None:
    """The ADR 0003 equivalence guarantee: schema-pass implies core-load."""
    from lexiqr import EntityResolver

    document = load(FIXTURE_PATH)
    validator.validate(document)

    report = EntityResolver.from_dict(document).transform("wo ist flooff", "de-DE")

    assert [match.canonical_id for match in report.matches] == ["product"]


def test_a_lexicon_without_a_schema_version_is_rejected(
    validator: Draft202012Validator,
) -> None:
    lexicon = load(FIXTURE_PATH)
    del lexicon["schemaVersion"]

    with pytest.raises(ValidationError):
        validator.validate(lexicon)
