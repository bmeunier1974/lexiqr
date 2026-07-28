"""The filter value type on its own — no lexicon, no index, no resolver.

`lexiqr.metadata` owns one thing: what a tenant may write in a filter, and what
holding it guarantees. That is testable with nothing else constructed, and it is
tested that way on purpose — a bound that only ever shows up through a loaded
lexicon is a bound whose reasoning has drifted somewhere else.

Every bound is checked at its limit and one past it, because a limit is a claim
about two values and asserting only the rejection leaves the accepted side of the
line to chance.
"""

from typing import Any

import pytest

from lexiqr.metadata import (
    MAX_KEY_LENGTH,
    MAX_KEYS,
    MAX_LIST_LENGTH,
    MAX_VALUE_LENGTH,
    Metadata,
    MetadataFault,
)

# --- The value domain: a scalar, or a set of scalars.


@pytest.mark.parametrize(
    ("value", "held"),
    [
        ("Movie", "Movie"),
        (12, 12),
        (7.5, 7.5),
        (True, True),
        (False, False),
        (["drama", "thriller"], ("drama", "thriller")),
    ],
)
def test_every_accepted_kind_of_filter_value_is_held_as_written(
    value: Any, held: Any
) -> None:
    """A list becomes a tuple — the value a caller is handed must not be mutable —
    and everything else is the value the tenant wrote."""
    assert Metadata.of({"filter": value})["filter"] == held


def test_a_boolean_stays_a_boolean_rather_than_becoming_a_number() -> None:
    """`bool` subclasses `int` in Python, so a careless type check reads `True` as
    the number 1 and hands a tenant's flag back as an integer."""
    assert Metadata.of({"streamable": True})["streamable"] is True


@pytest.mark.parametrize(
    "value", [None, {"equals": "Movie"}, [["drama"]], [1, 2], ("a", "b")]
)
def test_a_value_outside_the_domain_is_rejected_naming_its_key(value: Any) -> None:
    """No null — an absent key already means absent — and no nesting, which would
    invite the query language lexiqr deliberately does not have."""
    with pytest.raises(MetadataFault) as raised:
        Metadata.of({"productType": value})

    assert raised.value.field == "metadata.productType"


# --- The bounds, at the limit and one past it.


def test_a_filter_may_declare_the_maximum_number_of_keys() -> None:
    at_limit = {f"filter{n:02d}": "on" for n in range(MAX_KEYS)}

    assert len(Metadata.of(at_limit)) == MAX_KEYS


def test_one_key_past_the_maximum_is_rejected() -> None:
    too_many = {f"filter{n:02d}": "on" for n in range(MAX_KEYS + 1)}

    with pytest.raises(MetadataFault) as raised:
        Metadata.of(too_many)

    assert raised.value.field == "metadata"
    assert str(MAX_KEYS) in raised.value.reason


def test_a_key_at_the_maximum_length_is_accepted_and_one_over_is_not() -> None:
    longest = "k" * MAX_KEY_LENGTH

    assert longest in Metadata.of({longest: "on"})

    with pytest.raises(MetadataFault):
        Metadata.of({longest + "k": "on"})


@pytest.mark.parametrize("key", ["product type", "produkt!", "", "a/b"])
def test_a_key_outside_the_identifier_grammar_is_rejected(key: str) -> None:
    with pytest.raises(MetadataFault) as raised:
        Metadata.of({key: "on"})

    assert repr(key) in raised.value.reason


def test_a_string_value_at_the_maximum_length_is_accepted_and_one_over_is_not() -> None:
    longest = "M" * MAX_VALUE_LENGTH

    assert Metadata.of({"productType": longest})["productType"] == longest

    with pytest.raises(MetadataFault):
        Metadata.of({"productType": longest + "M"})


def test_a_list_at_the_maximum_length_is_accepted_and_one_over_is_not() -> None:
    longest = [f"genre{n:02d}" for n in range(MAX_LIST_LENGTH)]

    # Narrowed the way a strictly-typed caller would: the value type is a union,
    # so reading a list filter means asking whether this one is a list.
    held = Metadata.of({"genre": longest})["genre"]
    assert isinstance(held, tuple)
    assert len(held) == MAX_LIST_LENGTH

    with pytest.raises(MetadataFault):
        Metadata.of({"genre": [*longest, "genreXX"]})


@pytest.mark.parametrize("value", ["", []])
def test_an_empty_value_is_rejected(value: Any) -> None:
    """A key present with nothing in it says something the author did not mean."""
    with pytest.raises(MetadataFault) as raised:
        Metadata.of({"genre": value})

    assert raised.value.field == "metadata.genre"


@pytest.mark.parametrize("value", ["   ", "\t\n", ["drama", "  "]])
def test_a_whitespace_only_value_is_rejected(value: Any) -> None:
    """Beyond the schema, whose minLength cannot tell a value from a blank one.

    An accidental run of spaces must not become a live filter that silently
    narrows every query the consuming service builds.
    """
    with pytest.raises(MetadataFault) as raised:
        Metadata.of({"productType": value})

    assert "whitespace" in raised.value.reason


def test_a_repeated_value_in_a_list_is_rejected() -> None:
    with pytest.raises(MetadataFault):
        Metadata.of({"genre": ["drama", "drama"]})


def test_an_absent_declaration_is_the_empty_filter_and_an_empty_object_is_not() -> None:
    """Most entries carry no filter, so absent is ordinary. `{}` is a mistake."""
    assert len(Metadata.of(None)) == 0

    with pytest.raises(MetadataFault):
        Metadata.of({})


@pytest.mark.parametrize("declared", ["Movie", 7, ["genre"]])
def test_a_declaration_that_is_not_an_object_is_rejected(declared: Any) -> None:
    with pytest.raises(MetadataFault) as raised:
        Metadata.of(declared)

    assert raised.value.field == "metadata"


# --- What holding one guarantees: immutable, hashable, sorted.


def test_a_filter_cannot_be_mutated_by_whoever_was_handed_it() -> None:
    """Lexicon-derived data a caller holds must not be corruptible by the caller."""
    metadata = Metadata.of({"productType": "Movie"})

    with pytest.raises(TypeError):
        metadata["productType"] = "Series"  # type: ignore[index]


def test_a_filter_is_hashable_so_a_match_carrying_one_stays_usable() -> None:
    one = Metadata.of({"productType": "Movie", "genre": ["drama"]})
    same = Metadata.of({"genre": ["drama"], "productType": "Movie"})

    assert hash(one) == hash(same)
    assert len({one, same}) == 1


def test_two_filters_declaring_the_same_pairs_are_equal_whatever_the_order() -> None:
    assert Metadata.of({"a": "1", "b": "2"}) == Metadata.of({"b": "2", "a": "1"})
    assert Metadata.of({"a": "1"}) == {"a": "1"}


def test_a_filter_iterates_in_sorted_key_order() -> None:
    """So anything built from it — a serialization, a rendered line — is stable
    across runs and platforms without the caller having to sort."""
    metadata = Metadata.of({"productType": "Movie", "genre": ["drama"], "age": 12})

    assert list(metadata) == ["age", "genre", "productType"]
