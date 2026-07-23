"""Typo-tolerant resolution: the observable behaviour of the fuzzy second pass.

Every test here drives the public `EntityResolver.transform` and reads only the
match report — which text resolved to which entity, and what correction it
recorded. Nothing reaches into the residue tokenizer, the rapidfuzz scores, or
the order candidates were generated in; those are the fuzzy pass's private
business and are free to change.
"""

import json
from pathlib import Path
from typing import Any

from lexiqr import EntityResolver, ScoreTier
from lexiqr.lexicon import Lexicon

REPO_ROOT = Path(__file__).resolve().parent.parent
FLOOFF = REPO_ROOT / "examples" / "flooff.lexicon.json"


def one_entity(locale: str, canonical_id: str, singular: str) -> dict[str, Any]:
    """A one-entity lexicon, so a test states exactly the surface form it means."""
    return {
        "schemaVersion": "1",
        "defaultLocale": locale,
        "entities": {
            canonical_id: {"locales": {locale: {"preferred": {"singular": singular}}}}
        },
    }


def test_a_fuzzy_match_carries_the_same_fields_an_exact_match_does() -> None:
    resolver = EntityResolver.from_file(FLOOFF)

    fuzzy = resolver.transform("wo ist floof", "de-DE").matches[0]
    exact = resolver.transform("wo ist flooff", "de-DE").matches[0]

    assert fuzzy.canonical_id == exact.canonical_id == "product"
    assert fuzzy.surface_form == exact.surface_form == "flooff"
    assert fuzzy.score_tier is exact.score_tier is ScoreTier.PREFERRED
    assert fuzzy.matched_locale == exact.matched_locale == "de-DE"
    assert isinstance(fuzzy.span, tuple) and len(fuzzy.span) == 2


def test_an_exact_match_carries_no_correction() -> None:
    report = EntityResolver.from_file(FLOOFF).transform("wo ist flooff", "de-DE")

    assert report.matches[0].correction is None


def test_a_fuzzy_match_records_what_was_typed_and_resolves_the_declared_form() -> None:
    report = EntityResolver.from_file(FLOOFF).transform("wo ist floof", "de-DE")
    match = report.matches[0]

    assert match.correction == "floof"
    assert match.surface_form == "flooff"


def test_a_fuzzy_span_indexes_the_original_prompt_across_a_stripped_accent() -> None:
    # "prämie" folds to "pramie"; a transposed "prämei" is a near-miss of it.
    resolver = EntityResolver.from_dict(one_entity("de-DE", "bonus", "prämie"))

    match = resolver.transform("die prämei buchen", "de-DE").matches[0]
    start, end = match.span

    assert match.canonical_id == "bonus"
    assert "die prämei buchen"[start:end] == "prämei"
    assert match.correction == "prämei"


def test_a_fuzzy_span_survives_a_fold_that_changes_the_length() -> None:
    # "ß" folds to "ss", so "straaße" folds to the eight-char "straasse", a
    # near-miss of the seven-char "strasse". The span must still point back at
    # the seven-char word the user actually typed.
    resolver = EntityResolver.from_dict(one_entity("de-DE", "street", "strasse"))

    match = resolver.transform("die straaße entlang", "de-DE").matches[0]
    start, end = match.span

    assert match.canonical_id == "street"
    assert "die straaße entlang"[start:end] == "straaße"
    assert match.correction == "straaße"


def test_a_word_beyond_the_budget_returns_no_match_rather_than_a_wrong_one() -> None:
    report = EntityResolver.from_file(FLOOFF).transform("wo ist knurbel", "de-DE")

    assert report.matches == ()


def resolves(locale: str, canonical_id: str, singular: str, prompt: str) -> bool:
    """Whether `prompt` resolves to `canonical_id` through the fuzzy pass."""
    resolver = EntityResolver.from_dict(one_entity(locale, canonical_id, singular))
    matches = resolver.transform(prompt, locale).matches
    return any(match.canonical_id == canonical_id for match in matches)


def test_a_short_surface_form_matches_exactly_only() -> None:
    # "cat" is three characters: budget 0. A one-edit "cot" must not resolve,
    # or every three-letter word in a prompt would collide with it.
    assert not resolves("en-GB", "animal", "cat", "the cot sat")


def test_a_medium_surface_form_resolves_through_one_edit() -> None:
    # "table" is five characters: budget 1. "tablo" is one substitution away.
    assert resolves("en-GB", "furniture", "table", "clear the tablo")


def test_a_medium_surface_form_rejects_a_two_edit_variant() -> None:
    # "tablexy" is two edits from "table" yet still highly similar, so only the
    # length-aware budget — not the similarity threshold — can turn it away.
    assert not resolves("en-GB", "furniture", "table", "clear the tablexy")


def test_a_long_surface_form_resolves_through_two_edits() -> None:
    # "flooff" is six characters: budget 2. "flof" is two edits away.
    assert resolves("de-DE", "product", "flooff", "wo ist flof")


def test_a_long_surface_form_rejects_a_three_edit_variant() -> None:
    assert not resolves("de-DE", "product", "flooff", "wo ist flo")


def test_a_four_character_form_resolves_through_one_edit() -> None:
    # The just-inside case of the three/four boundary: at four characters the
    # budget opens to one edit, where at three it was closed.
    assert resolves("en-GB", "record", "item", "add itemx now")


def test_a_transposition_of_adjacent_characters_costs_one_edit() -> None:
    # "tabel" swaps two adjacent letters of the five-character "table". Plain
    # edit distance would score that two and exceed the budget of one; a
    # Damerau-style distance scores it one, so it resolves.
    assert resolves("en-GB", "furniture", "table", "clear the tabel")


def test_a_candidate_within_budget_but_below_similarity_does_not_resolve() -> None:
    # "flooaa" is two edits from "flooff" — inside the six-character budget — but
    # too dissimilar to stand behind, so the threshold turns it away.
    assert not resolves("de-DE", "product", "flooff", "wo ist flooaa")


def test_fuzzy_is_on_by_default_so_a_typo_resolves_without_configuration() -> None:
    report = EntityResolver.from_file(FLOOFF).transform("wo ist floof", "de-DE")

    assert report.matches[0].correction == "floof"


def test_fuzzy_false_turns_off_tolerance_but_keeps_exact_matching() -> None:
    resolver = EntityResolver.from_file(FLOOFF, fuzzy=False)

    assert resolver.transform("wo ist floof", "de-DE").matches == ()
    exact = resolver.transform("wo ist flooff", "de-DE")
    assert [match.canonical_id for match in exact.matches] == ["product"]


def test_fuzzy_false_produces_no_correction_anywhere() -> None:
    resolver = EntityResolver.from_file(FLOOFF, fuzzy=False)

    report = resolver.transform("wo ist flooff und floof", "de-DE")

    assert report.matches  # the correctly spelled term still resolves
    assert all(match.correction is None for match in report.matches)


def test_the_fuzzy_keyword_is_accepted_on_every_construction_path() -> None:
    document = json.loads(FLOOFF.read_text(encoding="utf-8"))

    resolvers = (
        EntityResolver.from_file(FLOOFF, fuzzy=False),
        EntityResolver.from_dict(document, fuzzy=False),
        EntityResolver(Lexicon.from_dict(document), fuzzy=False),
    )

    for resolver in resolvers:
        assert resolver.transform("wo ist floof", "de-DE").matches == ()


def test_the_fuzzy_pass_is_isolated_no_similarity_reasoning_leaks_elsewhere() -> None:
    import lexiqr

    package = Path(lexiqr.__file__).resolve().parent

    assert "rapidfuzz" in (package / "fuzzy.py").read_text(encoding="utf-8")
    for module in ("matcher.py", "resolver.py", "overlaps.py", "index.py"):
        assert "rapidfuzz" not in (package / module).read_text(encoding="utf-8")


def test_rapidfuzz_remains_the_only_runtime_dependency() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'dependencies = ["rapidfuzz>=3.0"]' in pyproject
