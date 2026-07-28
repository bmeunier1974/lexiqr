"""Determinism (C9) as property-based invariants over the public API.

Snapshot tests pin the cases we thought of; these pin the ones we didn't.
Hypothesis generates lexicons and prompts and asserts, as invariants that must
hold for every one of them, that resolution is deterministic, that no input
escapes the guard into an unhandled exception, and that every span it returns
indexes the original prompt. The invariants are stated over the public API
(`transform` + `serialize_report`), so they stay meaningful as the pipeline
evolves, and they are exercised across the full configuration surface — `fuzzy`
on and off, default and explicit fallback chains — because a guarantee that
holds only for defaults is not the guarantee C9 states.
"""

from __future__ import annotations

import string
from typing import Any

import pytest
from hypothesis import find, given, settings
from hypothesis import strategies as st

from conftest import lexicon_document
from lexiqr import EntityResolver, MatchReport, ValidationError, serialize_report

_WORD = st.text(alphabet=string.ascii_lowercase, min_size=3, max_size=8)
_LOCALES = ("de-DE", "en-US", "fr-FR")

# fuzzy on/off × default/explicit chain — the whole configuration surface.
_CONFIGS = [
    pytest.param(True, False, id="fuzzy-on/default-chain"),
    pytest.param(False, False, id="fuzzy-off/default-chain"),
    pytest.param(True, True, id="fuzzy-on/explicit-chain"),
    pytest.param(False, True, id="fuzzy-off/explicit-chain"),
]


@st.composite
def lexicon_and_prompt(draw: st.DrawFn) -> tuple[dict[str, Any], str]:
    """A valid lexicon plus a prompt built partly from its own vocabulary.

    Words are drawn globally unique and consumed once, so no surface form is
    ever claimed twice in a locale — the lexicon always loads. The prompt mixes
    real surface forms with noise words, so matches actually happen and the
    ordering rules are exercised rather than skirted.
    """
    pool = draw(st.lists(_WORD, min_size=2, max_size=24, unique=True))
    words = iter(pool)
    entities: dict[str, Any] = {}
    index = 0
    while True:
        singular = next(words, None)
        if singular is None:
            break
        index += 1
        locale = draw(st.sampled_from(_LOCALES))
        preferred: dict[str, str] = {"singular": singular}
        if draw(st.booleans()):
            plural = next(words, None)
            if plural is not None:
                preferred["plural"] = plural
        forms: dict[str, Any] = {"preferred": preferred}
        alternates = [
            w for w in (next(words, None) for _ in range(draw(st.integers(0, 2)))) if w
        ]
        if alternates:
            forms["alternates"] = alternates
        entities[f"e{index:03d}"] = {"locales": {locale: forms}}

    document = lexicon_document(
        default_locale=draw(st.sampled_from(_LOCALES)), entities=entities
    )

    lexicon_words = [
        value
        for entity in entities.values()
        for forms in entity["locales"].values()
        for value in (
            [forms["preferred"]["singular"]]
            + ([forms["preferred"]["plural"]] if "plural" in forms["preferred"] else [])
            + forms.get("alternates", [])
        )
    ]
    tokens = draw(
        st.lists(st.sampled_from(lexicon_words) | _WORD, min_size=0, max_size=8)
    )
    return document, " ".join(tokens)


def _declared_locales(document: dict[str, Any]) -> list[str]:
    return sorted(
        {
            locale
            for entity in document["entities"].values()
            for locale in entity["locales"]
        }
    )


@pytest.mark.parametrize(("fuzzy", "explicit_chain"), _CONFIGS)
@settings(deadline=None, max_examples=150)
@given(data=lexicon_and_prompt())
def test_repeated_resolution_is_byte_identical(
    data: tuple[dict[str, Any], str], fuzzy: bool, explicit_chain: bool
) -> None:
    document, prompt = data
    chain = _declared_locales(document) if explicit_chain else None
    locale = _declared_locales(document)[0]

    first = EntityResolver.from_dict(document, fuzzy=fuzzy, fallback_chain=chain)
    second = EntityResolver.from_dict(document, fuzzy=fuzzy, fallback_chain=chain)

    a = serialize_report(first.transform(prompt, locale))
    b = serialize_report(first.transform(prompt, locale))
    c = serialize_report(second.transform(prompt, locale))

    assert a == b == c


@pytest.mark.parametrize(("fuzzy", "explicit_chain"), _CONFIGS)
@settings(deadline=None, max_examples=150)
@given(data=lexicon_and_prompt(), noise=st.text(min_size=0, max_size=60))
def test_no_input_escapes_the_guard_and_spans_stay_valid(
    data: tuple[dict[str, Any], str],
    noise: str,
    fuzzy: bool,
    explicit_chain: bool,
) -> None:
    document, prompt = data
    chain = _declared_locales(document) if explicit_chain else None
    locale = _declared_locales(document)[0]
    resolver = EntityResolver.from_dict(document, fuzzy=fuzzy, fallback_chain=chain)

    for candidate in (prompt, noise, prompt + noise):
        try:
            report = resolver.transform(candidate, locale)
        except ValidationError:
            continue  # a defined, structured rejection — never an escape
        assert isinstance(report, MatchReport)
        for start, end in (match.span for match in report.matches):
            assert 0 <= start <= end <= len(report.prompt)
            assert report.prompt[start:end] != ""


def test_a_failing_property_shrinks_to_a_minimal_reproducing_case() -> None:
    """The shrinker these properties rely on reduces a counterexample to its
    minimum, not to whatever random value first tripped it — a failure lands as
    a readable input a maintainer can debug rather than a wall of noise.

    Standing in for a property failure: the smallest string satisfying "contains
    a digit" is the single character "0". If hypothesis returned an unshrunk
    example, this would be some long random text instead.
    """
    minimal = find(st.text(), lambda s: any(character.isdigit() for character in s))

    assert minimal == "0"
