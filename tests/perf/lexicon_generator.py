"""A seeded generator for the benchmark lexicon the perf gate measures against.

The performance envelope is stated against a realistic 1,000-surface-form
lexicon. That fixture is *generated*, not checked in: a seeded generator makes it
reviewable (this file is the fixture), regenerable, and — the load-bearing
property — byte-identical on every run, platform, and Python version, so a
measurement taken today is comparable to one taken last month.

Determinism comes from one place: a `random.Random(seed)` whose `random`,
`randint`, `choice`, and `sample` algorithms are fixed across CPython versions
and platforms. Nothing here reads the wall clock, unseeded randomness, or
unordered iteration — entities are emitted in counter order and each entity's
locales in sorted order, and the lexicon is serialized with sorted keys.

The lexicon is realistic rather than a thousand variations of one word: several
locales, and a mix of preferred singular (always), plural (most of the time),
and a handful of alternates. Every surface form is unique within its locale, so
the generated fixture never trips core's ambiguity check, and every form is a
short word, so it never trips the pathological-length check.
"""

from __future__ import annotations

import json
import random
from typing import Any

#: The seed the benchmark fixture is pinned to. Passing it (or any fixed seed)
#: yields the same lexicon every time; it is a constant so the gate and this
#: test measure the identical fixture.
BENCHMARK_SEED = 20260724

#: How many surface forms the fixture aims for. Generation stops once the count
#: first reaches this, so the total is this or a few more — a realistic tenant
#: vocabulary size, per the vision's envelope.
TARGET_SURFACE_FORMS = 1000

#: The pointer the published fixtures carry, mirrored so the generated document
#: looks like one an author would write.
_SCHEMA_URL = (
    "https://raw.githubusercontent.com/bmeunier1974/lexiqr/v0.0.1/"
    "schema/lexicon.v1.schema.json"
)

#: Locales the fixture spreads entities across — a multilingual tenant, which is
#: what lexiqr exists for.
_LOCALES = ("de-DE", "en-US", "fr-FR", "es-ES", "it-IT")

#: A pool of pronounceable syllables. Words are built from these so the fixture
#: reads like jargon rather than like `word_0001`, while staying easy to review.
_SYLLABLES = (
    "ba",
    "ko",
    "mi",
    "tan",
    "lor",
    "vex",
    "nu",
    "ral",
    "sen",
    "dor",
    "pi",
    "que",
    "fa",
    "zel",
    "mo",
    "rin",
    "tas",
    "vol",
    "gu",
    "nex",
    "sar",
    "tup",
    "wen",
    "lok",
    "bir",
    "cae",
    "dun",
    "fel",
    "hop",
    "jun",
)


def generate_benchmark_lexicon(
    *, seed: int = BENCHMARK_SEED, target_surface_forms: int = TARGET_SURFACE_FORMS
) -> dict[str, Any]:
    """Return a schema-valid lexicon of about `target_surface_forms` forms.

    Deterministic in `seed`: same seed, byte-identical lexicon.
    """
    rng = random.Random(seed)
    used_by_locale: dict[str, set[str]] = {locale: set() for locale in _LOCALES}
    entities: dict[str, Any] = {}
    forms = 0
    index = 0

    def fresh(locale: str) -> str:
        """A word not yet used in this locale — keeps every form unambiguous."""
        while True:
            length = rng.randint(2, 4)
            word = "".join(rng.choice(_SYLLABLES) for _ in range(length))
            if word not in used_by_locale[locale]:
                used_by_locale[locale].add(word)
                return word

    while forms < target_surface_forms:
        index += 1
        canonical_id = f"entity_{index:04d}"
        chosen = sorted(rng.sample(_LOCALES, rng.randint(1, len(_LOCALES))))
        locales: dict[str, Any] = {}
        for locale in chosen:
            preferred: dict[str, str] = {"singular": fresh(locale)}
            forms += 1
            if rng.random() < 0.7:
                preferred["plural"] = fresh(locale)
                forms += 1
            surface_forms: dict[str, Any] = {"preferred": preferred}
            alternates = [fresh(locale) for _ in range(rng.randint(0, 3))]
            forms += len(alternates)
            if alternates:
                surface_forms["alternates"] = alternates
            locales[locale] = surface_forms
        entities[canonical_id] = {"locales": locales}

    return {
        "$schema": _SCHEMA_URL,
        "schemaVersion": "1",
        "defaultLocale": "de-DE",
        "entities": entities,
    }


def count_surface_forms(lexicon: dict[str, Any]) -> int:
    """Count every declared surface form: singular, plural, and each alternate."""
    total = 0
    for entity in lexicon["entities"].values():
        for forms in entity["locales"].values():
            preferred = forms["preferred"]
            total += 1  # singular is required
            total += 1 if "plural" in preferred else 0
            total += len(forms.get("alternates", ()))
    return total


def serialize_lexicon(lexicon: dict[str, Any]) -> str:
    """Canonical text form of a generated lexicon: sorted keys, stable, ASCII.

    This is what makes "byte-identical every run" checkable and what a
    regenerated fixture would be written to disk as if one ever were.
    """
    return json.dumps(lexicon, sort_keys=True, ensure_ascii=True, indent=2) + "\n"
