"""The public API surface: `from lexiqr import EntityResolver` (ADR 0002).

Everything named here is semver-governed. A name that leaves this list, or
changes shape, is a breaking release.
"""

import lexiqr


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
