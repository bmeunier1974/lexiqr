"""Accent-insensitive matching whose spans still index the original prompt.

Normalization is the one stage allowed to change the text, so it is the one
stage that has to hand back a way home. Every assertion here slices
`report.prompt` — the string the user actually typed — with the span it was
given, because that is what an integrating developer does with a match.
"""

from typing import Any

from lexiqr import EntityResolver


def lexicon(locale: str, singular: str, **preferred: str) -> dict[str, Any]:
    """A one-entity lexicon, so a test can state exactly the surface form it means."""
    return {
        "schemaVersion": "1",
        "defaultLocale": locale,
        "entities": {
            "episode": {
                "locales": {locale: {"preferred": {"singular": singular, **preferred}}}
            }
        },
    }


def test_an_accented_prompt_matches_a_surface_form_written_without_accents() -> None:
    resolver = EntityResolver.from_dict(lexicon("fr-FR", "episodes"))

    report = resolver.transform("combien d'épisodes", "fr-FR")

    assert [match.canonical_id for match in report.matches] == ["episode"]
    start, end = report.matches[0].span
    assert report.prompt[start:end] == "épisodes"


def test_an_unaccented_prompt_matches_a_surface_form_a_tenant_wrote_with_accents() -> (
    None
):
    resolver = EntityResolver.from_dict(lexicon("fr-FR", "épisodes"))

    report = resolver.transform("combien d'episodes", "fr-FR")

    assert [match.canonical_id for match in report.matches] == ["episode"]
    start, end = report.matches[0].span
    assert report.prompt[start:end] == "episodes"


def test_a_capitalised_prompt_matches_a_lowercase_surface_form() -> None:
    resolver = EntityResolver.from_dict(lexicon("fr-FR", "épisodes"))

    report = resolver.transform("Épisodes disponibles", "fr-FR")

    assert [match.canonical_id for match in report.matches] == ["episode"]
    start, end = report.matches[0].span
    assert report.prompt[start:end] == "Épisodes"


def test_a_span_survives_a_fold_that_lengthens_the_text() -> None:
    """`ß` casefolds to `ss`, so every offset after it drifts by one."""
    resolver = EntityResolver.from_dict(lexicon("de-DE", "strasse"))

    report = resolver.transform("die Straße und die Gasse", "de-DE")

    assert [match.canonical_id for match in report.matches] == ["episode"]
    start, end = report.matches[0].span
    assert report.prompt[start:end] == "Straße"


def test_a_span_after_a_stripped_accent_is_not_shifted_by_the_stripping() -> None:
    """A decomposed accent is dropped, so offsets after it drift the other way."""
    resolver = EntityResolver.from_dict(lexicon("fr-FR", "diffuses"))

    report = resolver.transform("épisodes diffusés hier", "fr-FR")

    start, end = report.matches[0].span
    assert report.prompt[start:end] == "diffusés"
