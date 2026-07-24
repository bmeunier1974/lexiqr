"""The pure validation-error renderer: typed error(s) in, string out.

These tests construct core's `ValidationError` values directly and assert the
text the renderer returns. No argv, no process, no captured streams — the whole
point of the renderer being a pure function is that it can be checked this way.
"""

from lexiqr import ValidationError
from lexiqr.cli._validation import render_valid_lexicon, render_validation_errors


def test_a_valid_lexicon_is_confirmed_plainly_and_names_its_source() -> None:
    confirmation = render_valid_lexicon("tenant.lexicon.json")

    assert "tenant.lexicon.json" in confirmation
    assert "valid" in confirmation.lower()


def test_a_single_error_names_the_entity_locale_and_field_it_faults() -> None:
    error = ValidationError(
        "Entity 'product', locale 'de-DE': field 'preferred.singular' is required.",
        canonical_id="product",
        locale="de-DE",
        field="preferred.singular",
    )

    rendered = render_validation_errors("tenant.json", [error])

    assert "product" in rendered
    assert "de-DE" in rendered
    assert "preferred.singular" in rendered
    assert "invalid" in rendered.lower()


def test_a_document_level_error_without_coordinates_still_renders() -> None:
    error = ValidationError(
        "Unsupported lexicon schemaVersion '99'.", field="schemaVersion"
    )

    rendered = render_validation_errors("tenant.json", [error])

    assert "schemaVersion" in rendered
    assert "99" in rendered


def test_every_error_is_reported_not_just_the_first() -> None:
    errors = [
        ValidationError(
            "Entity 'alpha', locale 'de-DE': field 'preferred.singular' is required.",
            canonical_id="alpha",
            locale="de-DE",
            field="preferred.singular",
        ),
        ValidationError(
            "Entity 'bravo', locale 'fr-FR': field 'alternates[0]' is empty.",
            canonical_id="bravo",
            locale="fr-FR",
            field="alternates[0]",
        ),
    ]

    rendered = render_validation_errors("tenant.json", errors)

    assert "alpha" in rendered
    assert "bravo" in rendered
    assert "2 errors" in rendered


def test_multiple_errors_render_in_a_deterministic_order() -> None:
    first = ValidationError(
        "Entity 'alpha', locale 'de-DE': field 'preferred.singular' is required.",
        canonical_id="alpha",
        locale="de-DE",
        field="preferred.singular",
    )
    second = ValidationError(
        "Entity 'bravo', locale 'fr-FR': field 'alternates[0]' is empty.",
        canonical_id="bravo",
        locale="fr-FR",
        field="alternates[0]",
    )

    forward = render_validation_errors("tenant.json", [first, second])
    reverse = render_validation_errors("tenant.json", [second, first])

    assert forward == reverse
    assert forward.index("alpha") < forward.index("bravo")


def test_a_single_error_is_counted_in_the_singular() -> None:
    error = ValidationError(
        "Unsupported lexicon schemaVersion '99'.", field="schemaVersion"
    )

    rendered = render_validation_errors("tenant.json", [error])

    assert "1 error" in rendered
    assert "1 errors" not in rendered
