"""The benchmark lexicon generator must be deterministic — verified, not assumed.

A performance measurement is only comparable over time if the lexicon behind it
is byte-identical every run, on every platform and Python version. A
nondeterministic fixture would silently poison every measurement built on it, so
the generator's determinism is a tested guarantee. These tests assert observable
outputs — the serialized lexicon, the surface-form count, the set of locales,
and that core accepts it — never the generator's internals.
"""

import json

import jsonschema
import pytest

from conftest import REPO_ROOT
from lexiqr import EntityResolver, ValidationError
from perf.lexicon_generator import (
    BENCHMARK_SEED,
    count_surface_forms,
    generate_benchmark_lexicon,
    serialize_lexicon,
)

PUBLISHED_SCHEMA = REPO_ROOT / "schema" / "lexicon.v1.schema.json"


def test_generating_twice_with_the_same_seed_is_byte_identical() -> None:
    first = serialize_lexicon(generate_benchmark_lexicon(seed=BENCHMARK_SEED))
    second = serialize_lexicon(generate_benchmark_lexicon(seed=BENCHMARK_SEED))

    assert first == second


def test_the_lexicon_carries_about_a_thousand_surface_forms() -> None:
    lexicon = generate_benchmark_lexicon(seed=BENCHMARK_SEED)

    count = count_surface_forms(lexicon)

    assert 1000 <= count <= 1050


def test_the_lexicon_spans_multiple_locales() -> None:
    lexicon = generate_benchmark_lexicon(seed=BENCHMARK_SEED)

    locales = {
        locale
        for entity in lexicon["entities"].values()
        for locale in entity["locales"]
    }

    assert len(locales) >= 3


def test_the_lexicon_carries_a_mix_of_preferred_plural_and_alternate_forms() -> None:
    lexicon = generate_benchmark_lexicon(seed=BENCHMARK_SEED)

    has_plural = has_alternates = False
    for entity in lexicon["entities"].values():
        for forms in entity["locales"].values():
            has_plural = has_plural or "plural" in forms["preferred"]
            has_alternates = has_alternates or bool(forms.get("alternates"))

    assert has_plural
    assert has_alternates


def test_a_different_seed_produces_a_different_lexicon() -> None:
    one = serialize_lexicon(generate_benchmark_lexicon(seed=BENCHMARK_SEED))
    other = serialize_lexicon(generate_benchmark_lexicon(seed=BENCHMARK_SEED + 1))

    assert one != other


def test_the_generated_lexicon_validates_against_the_published_schema() -> None:
    schema = json.loads(PUBLISHED_SCHEMA.read_text(encoding="utf-8"))
    lexicon = generate_benchmark_lexicon(seed=BENCHMARK_SEED)

    jsonschema.Draft202012Validator(schema).validate(lexicon)


def test_core_accepts_the_generated_lexicon_without_rejecting_it() -> None:
    lexicon = generate_benchmark_lexicon(seed=BENCHMARK_SEED)

    try:
        EntityResolver.from_dict(lexicon)
    except ValidationError as rejected:  # pragma: no cover - failure detail
        pytest.fail(f"the benchmark lexicon must load cleanly, but: {rejected}")


def test_every_entry_of_the_benchmark_lexicon_carries_a_filter() -> None:
    """The envelope is claimed for a lexicon that uses the feature, not one that
    ignores it — so the fixture the gate measures has to use it everywhere.

    Without this the perf gate would pass on a lexicon with no metadata at all and
    the claim "adopting filters costs nothing per request" would be untested.
    """
    entities = generate_benchmark_lexicon(seed=BENCHMARK_SEED)["entities"]

    assert entities
    assert all(entity.get("metadata") for entity in entities.values())


def test_the_benchmark_filters_exercise_every_kind_of_value() -> None:
    """A bag of one string would not exercise holding, hashing, or serializing the
    list case, which is the one with a per-value cost."""
    kinds = {
        type(value)
        for entity in generate_benchmark_lexicon(seed=BENCHMARK_SEED)[
            "entities"
        ].values()
        for value in entity["metadata"].values()
    }

    assert {str, int, bool, list} <= kinds
