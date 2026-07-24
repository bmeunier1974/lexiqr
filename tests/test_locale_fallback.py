"""Locale fallback: a prompt in one variant resolves through a sibling variant.

Two things are asserted here, and only these two — never how the chain is built
internally. First, the pure chain builder: given the locales a lexicon actually
declares and the locale a caller asked for, which locales get walked and in what
order. Second, the end-to-end behaviour through `EntityResolver`: a `de-AT`
prompt resolving against `de-DE` surface forms, the requested locale winning
when it too could match, and the report naming the locale that answered.
"""

from pathlib import Path
from typing import Any

import pytest

from lexiqr import EntityResolver
from lexiqr.errors import ValidationError
from lexiqr.fallback import build_chain, resolve_explicit_chain

MEDIEN_DE = (
    Path(__file__).resolve().parent.parent
    / "schema"
    / "fixtures"
    / "valid"
    / "medien-de.lexicon.json"
)


# --- The chain builder, in isolation (no matching pipeline) -----------------


def test_the_exact_requested_locale_is_the_head_of_the_chain() -> None:
    assert build_chain("de-DE", ["de-DE", "de-AT", "de-CH"], "de-DE")[0] == "de-DE"


def test_same_language_siblings_follow_the_exact_locale() -> None:
    assert build_chain("de-DE", ["de-DE", "de-AT", "en-GB"], "de-DE") == (
        "de-DE",
        "de-AT",
    )


def test_a_requested_locale_absent_from_the_lexicon_falls_to_its_siblings() -> None:
    assert build_chain("de-AT", ["de-DE"], "de-DE") == ("de-DE",)


def test_an_unrelated_language_enters_the_chain_only_as_the_declared_default() -> None:
    # en-GB and fr-FR are unrelated to de; neither is the default, so neither
    # is walked. (The declared default's own place is asserted below.)
    assert build_chain("de-DE", ["de-DE", "en-GB", "fr-FR"], "de-DE") == ("de-DE",)


def test_tags_are_compared_case_insensitively() -> None:
    chain = build_chain("DE-de", ["de-DE", "DE-at"], "de-DE")

    assert chain[0].casefold() == "de-de"
    assert {tag.casefold() for tag in chain} == {"de-de", "de-at"}


def test_the_sibling_order_is_deterministic_and_deduplicated() -> None:
    one = build_chain("de-DE", ["de-DE", "de-AT", "de-CH", "de-DE"], "de-DE")
    another = build_chain("de-DE", ["de-CH", "de-AT", "de-DE"], "de-DE")

    assert one == another == ("de-DE", "de-AT", "de-CH")


# --- The declared default as the final backstop (story #37) -----------------


def test_the_declared_default_ends_a_chain_whose_language_has_no_variant() -> None:
    # fr-FR has no variant in the lexicon; the declared default de-DE ends it.
    assert build_chain("fr-FR", ["de-DE", "en-GB"], "de-DE") == ("de-DE",)


def test_the_default_is_tried_after_the_exact_locale_and_its_siblings() -> None:
    chain = build_chain("de-DE", ["de-DE", "de-AT", "en-GB"], "en-GB")

    assert chain == ("de-DE", "de-AT", "en-GB")


def test_the_declared_default_is_never_walked_twice() -> None:
    # The requested locale is itself the default; it appears once, at the head.
    assert build_chain("de-DE", ["de-DE", "de-AT"], "de-DE") == ("de-DE", "de-AT")


def test_a_declared_default_absent_from_the_lexicon_is_dropped() -> None:
    assert build_chain("fr-FR", ["en-GB"], "de-DE") == ()


# --- Explicit chain resolution and validation (story #38) -------------------


def test_an_explicit_chain_keeps_only_present_locales_in_the_order_given() -> None:
    assert resolve_explicit_chain(
        ["en-GB", "de-DE"], ["de-DE", "de-AT", "en-GB"]
    ) == ("en-GB", "de-DE")


def test_an_explicit_chain_drops_locales_absent_from_the_lexicon() -> None:
    assert resolve_explicit_chain(["fr-FR", "de-DE"], ["de-DE"]) == ("de-DE",)


def test_an_explicit_chain_matches_the_lexicon_case_insensitively() -> None:
    assert resolve_explicit_chain(["DE-de"], ["de-DE"]) == ("de-DE",)


def test_an_explicit_chain_deduplicates_keeping_the_first_position() -> None:
    assert resolve_explicit_chain(
        ["de-DE", "de-AT", "de-DE"], ["de-DE", "de-AT"]
    ) == ("de-DE", "de-AT")


def test_an_empty_explicit_chain_is_rejected() -> None:
    with pytest.raises(ValidationError):
        resolve_explicit_chain([], ["de-DE"])


def test_an_explicit_chain_of_only_absent_locales_is_rejected() -> None:
    with pytest.raises(ValidationError):
        resolve_explicit_chain(["fr-FR"], ["de-DE"])


# --- End to end through the resolver ----------------------------------------


def _de_variants() -> dict[str, Any]:
    """`product` authored only in de-DE; `invoice` in both de-DE and de-AT."""
    return {
        "schemaVersion": "1",
        "defaultLocale": "de-DE",
        "entities": {
            "product": {"locales": {"de-DE": {"preferred": {"singular": "flooff"}}}},
            "invoice": {
                "locales": {
                    "de-DE": {"preferred": {"singular": "rechnung"}},
                    "de-AT": {"preferred": {"singular": "rechnung"}},
                }
            },
        },
    }


def test_a_de_at_prompt_resolves_through_de_de_surface_forms() -> None:
    resolver = EntityResolver.from_dict(_de_variants())

    report = resolver.transform("wo ist flooff", "de-AT")

    assert [match.canonical_id for match in report.matches] == ["product"]
    assert all(match.matched_locale == "de-DE" for match in report.matches)
    assert report.locale == "de-DE"


def test_the_exact_requested_locale_answers_and_the_walk_stops_there() -> None:
    # "rechnung" is declared in both de-AT and de-DE; the requested de-AT wins.
    report = EntityResolver.from_dict(_de_variants()).transform(
        "die rechnung bitte", "de-AT"
    )

    assert [match.canonical_id for match in report.matches] == ["invoice"]
    assert all(match.matched_locale == "de-AT" for match in report.matches)
    assert report.locale == "de-AT"


def test_a_prompt_matching_nothing_in_the_chain_keeps_the_requested_locale() -> None:
    report = EntityResolver.from_dict(_de_variants()).transform(
        "wo ist der bahnhof", "de-AT"
    )

    assert report.matches == ()
    assert report.locale == "de-AT"


def test_spans_and_tiers_are_identical_on_a_fallback_match() -> None:
    resolver = EntityResolver.from_dict(_de_variants())

    fallback = resolver.transform("wo ist flooff", "de-AT").matches[0]
    direct = resolver.transform("wo ist flooff", "de-DE").matches[0]

    assert fallback.span == direct.span
    assert fallback.score_tier == direct.score_tier


def test_repeated_transforms_return_identical_reports() -> None:
    resolver = EntityResolver.from_dict(_de_variants())

    assert resolver.transform("wo ist flooff", "de-AT") == resolver.transform(
        "wo ist flooff", "de-AT"
    )


def test_the_sibling_variant_fixture_drives_fallback_end_to_end() -> None:
    report = EntityResolver.from_file(MEDIEN_DE).transform("wo ist flooff", "de-AT")

    assert [match.canonical_id for match in report.matches] == ["product"]
    assert report.matches[0].matched_locale == "de-DE"
    assert report.locale == "de-DE"


def test_an_unrelated_locale_resolves_through_the_declared_default() -> None:
    # defaultLocale is de-DE; a fr-FR prompt has no variant, so it backstops there.
    resolver = EntityResolver.from_dict(_de_variants())

    report = resolver.transform("wo ist flooff", "fr-FR")

    assert [match.canonical_id for match in report.matches] == ["product"]
    assert all(match.matched_locale == "de-DE" for match in report.matches)
    assert report.locale == "de-DE"


def test_nothing_matching_even_in_the_default_stays_an_empty_result() -> None:
    resolver = EntityResolver.from_dict(_de_variants())

    report = resolver.transform("wo ist der bahnhof", "fr-FR")

    assert report.matches == ()
    assert report.locale == "fr-FR"


# --- Explicit chain through the resolver (story #38) ------------------------


def test_an_explicit_chain_replaces_the_default_policy() -> None:
    # The default policy would answer "rechnung" in de-AT (the requested locale);
    # an explicit chain of only de-DE forces the walk there instead.
    resolver = EntityResolver.from_dict(_de_variants(), fallback_chain=["de-DE"])

    report = resolver.transform("die rechnung bitte", "de-AT")

    assert all(match.matched_locale == "de-DE" for match in report.matches)
    assert report.matches


def test_an_explicit_chain_walks_locales_in_the_order_given() -> None:
    de_first = EntityResolver.from_dict(
        _de_variants(), fallback_chain=["de-DE", "de-AT"]
    )
    at_first = EntityResolver.from_dict(
        _de_variants(), fallback_chain=["de-AT", "de-DE"]
    )

    assert (
        de_first.transform("die rechnung bitte", "de-DE").matches[0].matched_locale
        == "de-DE"
    )
    assert (
        at_first.transform("die rechnung bitte", "de-DE").matches[0].matched_locale
        == "de-AT"
    )


def test_from_file_accepts_an_explicit_chain() -> None:
    resolver = EntityResolver.from_file(MEDIEN_DE, fallback_chain=["de-DE"])

    report = resolver.transform("wo ist flooff", "de-AT")

    assert report.matches[0].matched_locale == "de-DE"


def test_an_absent_locale_in_the_chain_is_dropped_and_the_rest_proceed() -> None:
    resolver = EntityResolver.from_dict(
        _de_variants(), fallback_chain=["fr-FR", "de-DE"]
    )

    report = resolver.transform("wo ist flooff", "de-AT")

    assert report.matches[0].matched_locale == "de-DE"


def test_an_all_absent_explicit_chain_raises_at_construction() -> None:
    with pytest.raises(ValidationError):
        EntityResolver.from_dict(_de_variants(), fallback_chain=["fr-FR", "es-ES"])


def test_an_empty_explicit_chain_raises_before_any_transform_call() -> None:
    with pytest.raises(ValidationError):
        EntityResolver.from_dict(_de_variants(), fallback_chain=[])


def test_omitting_the_chain_leaves_the_default_policy_in_place() -> None:
    resolver = EntityResolver.from_dict(_de_variants())

    report = resolver.transform("die rechnung bitte", "de-AT")

    assert report.matches[0].matched_locale == "de-AT"
