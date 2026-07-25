"""The public API surface — everything `from lexiqr import …` may name (ADR 0002).

The resolution path (`EntityResolver` and the report types), the lexicon model
that path takes, and the two documented limits. Every name here is
semver-governed: one that leaves the list, or changes shape, is a breaking
release.

`PUBLIC_SURFACE` below is the tripwire: it is written out by hand, so widening
the surface is a decision someone takes in this file, and any name that reaches
`lexiqr.__all__` without being written here fails as the accidental export it is.
"""

from pathlib import Path

import pytest

import lexiqr
from conftest import FLOOFF_LEXICON

#: Every name lexiqr exports, and nothing else. Adding one is a minor release;
#: removing or reshaping one is a major release (README → Versioning and
#: compatibility).
PUBLIC_SURFACE = {
    "EntityMatch",
    "EntityResolver",
    "Lexicon",
    "MAX_PROMPT_LENGTH",
    "MAX_SURFACE_FORM_LENGTH",
    "MalformedDocumentError",
    "MatchReport",
    "ScoreTier",
    "SurfaceForms",
    "ValidationError",
    "deserialize_report",
    "serialize_report",
}


def test_the_public_surface_is_exactly_the_names_semver_governs() -> None:
    assert set(lexiqr.__all__) == PUBLIC_SURFACE


def test_every_exported_name_is_reachable_from_the_package_root() -> None:
    """What a consumer's `from lexiqr import *` actually brings in: each name in
    the list resolves, and nothing resolves that the list does not name."""
    imported: dict[str, object] = {}
    exec("from lexiqr import *", imported)

    assert set(imported) - {"__builtins__"} == PUBLIC_SURFACE


def test_entity_resolver_is_importable_from_the_package_root() -> None:
    from lexiqr import EntityResolver

    assert EntityResolver is not None


def test_validation_error_is_part_of_the_public_api() -> None:
    from lexiqr import ValidationError

    assert "ValidationError" in lexiqr.__all__
    assert issubclass(ValidationError, Exception)


def test_a_validation_error_carries_the_entity_locale_and_field_it_faults() -> None:
    error = lexiqr.ValidationError(
        "Entity 'product', locale 'de-DE': field 'preferred.singular' is required.",
        canonical_id="product",
        locale="de-DE",
        field="preferred.singular",
    )

    assert error.canonical_id == "product"
    assert error.locale == "de-DE"
    assert error.field == "preferred.singular"
    assert str(error) == error.message


def test_coordinates_a_failure_does_not_have_are_none() -> None:
    error = lexiqr.ValidationError("Unsupported schemaVersion.", field="schemaVersion")

    assert error.canonical_id is None
    assert error.locale is None


def test_a_file_that_is_not_json_at_all_faults_as_a_malformed_document(
    tmp_path: Path,
) -> None:
    """The file never became a document, so there was nothing to validate.

    Distinguishable on its own — a caller can tell "your path points at
    something that is not a lexicon file" from "your lexicon says the wrong
    thing", which is what lets the CLI give the two different exit codes without
    re-wording either message.
    """
    from lexiqr import Lexicon, MalformedDocumentError, ValidationError

    path = tmp_path / "truncated.lexicon.json"
    path.write_text('{"schemaVersion": "1",', encoding="utf-8")

    with pytest.raises(MalformedDocumentError) as raised:
        Lexicon.from_file(path)

    assert isinstance(raised.value, ValidationError)
    assert "JSON" in raised.value.message
    assert str(path) in raised.value.message


def test_a_document_that_parsed_but_is_wrong_is_not_a_malformed_document() -> None:
    """The other side of the distinction: a lexicon fault stays a lexicon fault,
    so code that catches the malformed-document case cannot swallow one."""
    from lexiqr import Lexicon, MalformedDocumentError, ValidationError

    with pytest.raises(ValidationError) as raised:
        Lexicon.from_dict({"schemaVersion": "99", "entities": {}})

    assert not isinstance(raised.value, MalformedDocumentError)


# --- The lexicon seam: `Lexicon` is the declared parameter type of the public
# --- constructor, so an integrating developer must be able to hold one — and to
# --- load and validate a tenant's file — without building a throwaway resolver.


def test_a_lexicon_loads_and_validates_through_exported_names_alone() -> None:
    from lexiqr import Lexicon, SurfaceForms

    lexicon = Lexicon.from_file(FLOOFF_LEXICON)

    assert lexicon.default_locale == "de-DE"
    forms = lexicon.entities["product"]["de-DE"]
    assert isinstance(forms, SurfaceForms)
    assert forms.preferred_singular == "flooff"


def test_loading_an_invalid_lexicon_faults_where_the_document_is_wrong() -> None:
    """Validation is construction: `from_dict` is the validate-only workflow."""
    from lexiqr import Lexicon, ValidationError

    with pytest.raises(ValidationError) as raised:
        Lexicon.from_dict({"schemaVersion": "99", "entities": {}})

    assert raised.value.field == "schemaVersion"


def test_a_resolver_is_built_from_a_lexicon_the_caller_already_holds() -> None:
    from lexiqr import EntityResolver, Lexicon

    resolver = EntityResolver(Lexicon.from_file(FLOOFF_LEXICON))

    assert resolver.transform("wo ist flooff", "de-DE").matches[0].canonical_id == (
        "product"
    )


# --- The two documented limits: fixed parts of the contract, not per-call
# --- arguments or configuration knobs. Their values are what the README (prompt
# --- length) and docs/lexicon-semantic-checks.md (surface-form length) state;
# --- changing either is a semver-visible change, so both are pinned here.


def test_the_documented_prompt_limit_is_a_public_constant() -> None:
    from lexiqr import MAX_PROMPT_LENGTH

    assert MAX_PROMPT_LENGTH == 10_000


def test_the_documented_surface_form_limit_is_a_public_constant() -> None:
    from lexiqr import MAX_SURFACE_FORM_LENGTH

    assert MAX_SURFACE_FORM_LENGTH == 128


@pytest.mark.parametrize(
    "private",
    ["check_prompt", "is_blank", "normalize_text", "build_chain", "scan"],
)
def test_no_private_machinery_rides_along_with_the_widened_surface(
    private: str,
) -> None:
    """Widening the seam exports the lexicon model and the two limits — not the
    fallback, guard, matcher, or normalizer machinery behind them. A name pulled
    into the package root but left out of `__all__` would still be reachable, so
    reachability is what is asserted here, not membership."""
    assert not hasattr(lexiqr, private)
