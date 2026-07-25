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


def test_arabic_keeps_its_diacritics_through_normalisation() -> None:
    """Harakat are combining marks, but they are not French accents.

    Latin-script folding treats a combining mark as decoration to discard.
    Applied to Arabic that is not folding, it is damage.
    """
    from lexiqr.normalizer import normalize

    folded = normalize("مُنتَج", "ar-EG")

    assert folded.text == "مُنتَج"


def test_arabic_letters_that_differ_only_by_hamza_are_not_conflated() -> None:
    """`أ` decomposes to `ا` + hamza; stripping the hamza invents a match."""
    resolver = EntityResolver.from_dict(lexicon("ar-EG", "اسم"))

    report = resolver.transform("أسم الحلقة", "ar-EG")

    assert report.matches == ()


def test_the_script_policy_reads_the_language_subtag_whatever_its_casing() -> None:
    """`AR-eg` names the same language as `ar-EG`: the subtag is folded first."""
    resolver = EntityResolver.from_dict(lexicon("AR-eg", "اسم"))

    assert resolver.transform("أسم الحلقة", "AR-eg").matches == ()
    assert resolver.transform("اسم الحلقة", "AR-eg").matches != ()


def test_an_arabic_prompt_resolves_with_a_span_that_slices_the_original() -> None:
    resolver = EntityResolver.from_dict(lexicon("ar-EG", "منتج", plural="منتجات"))

    report = resolver.transform("أين منتجات الشركة", "ar-EG")

    assert [match.canonical_id for match in report.matches] == ["episode"]
    start, end = report.matches[0].span
    assert report.prompt[start:end] == "منتجات"


def test_an_arabic_prompt_with_harakat_matches_a_form_written_the_same_way() -> None:
    resolver = EntityResolver.from_dict(lexicon("ar-EG", "مُنتَج"))

    report = resolver.transform("أين مُنتَج الشركة", "ar-EG")

    start, end = report.matches[0].span
    assert report.prompt[start:end] == "مُنتَج"
