"""Loading an entry: the target it resolves to, and the rules that come with it.

The key an entity object sits under is the **entry ID**; `canonicalId` is the
entity a match resolves to, and it defaults to the entry ID. These tests specify
that reading, and the checks the reading makes necessary — asserted through
`Lexicon`, the public loader, in the coordinate style every other validation
error in this suite is asserted in.
"""

import pytest

from conftest import lexicon_document
from lexiqr import Lexicon, ValidationError


def entry(singular: str = "film", **fields: object) -> dict[str, object]:
    return {"locales": {"de-DE": {"preferred": {"singular": singular}}}, **fields}


def test_an_entry_that_names_no_target_resolves_to_itself() -> None:
    """The default that keeps every lexicon written before the field meaningful.

    An author who has one word per entity never learns the field exists, and the
    entry ID goes on being the canonical ID — not because the loader special-cases
    the simple lexicon, but because that *is* the simple lexicon's meaning.
    """
    lexicon = Lexicon.from_dict(lexicon_document("de-DE", product=entry("flooff")))

    assert lexicon.entries["product"].canonical_id == "product"


def test_several_entries_may_resolve_to_one_entity() -> None:
    """The model an integrating developer reads: which entry, and what it means."""
    lexicon = Lexicon.from_dict(
        lexicon_document(
            "de-DE",
            movie=entry("film", canonicalId="product"),
            series=entry("serie", canonicalId="product"),
        )
    )

    assert [
        (entry_id, declared.entry_id, declared.canonical_id)
        for entry_id, declared in lexicon.entries.items()
    ] == [("movie", "movie", "product"), ("series", "series", "product")]


def test_a_target_that_is_itself_an_entry_with_another_target_is_rejected() -> None:
    """A target must be a leaf, not a link.

    `feature_film` → `movie` → `product` reads as though it resolves to `product`,
    and there is no honest answer to what it means: following the chain invents a
    rule the format does not state, and not following it leaves a match reporting
    `movie`, an entity no backend queries.
    """
    with pytest.raises(ValidationError) as raised:
        Lexicon.from_dict(
            lexicon_document(
                "de-DE",
                movie=entry("film", canonicalId="product"),
                feature_film=entry("spielfilm", canonicalId="movie"),
            )
        )

    assert raised.value.canonical_id == "feature_film"
    assert raised.value.field == "canonicalId"
    assert "movie" in raised.value.message
    assert "product" in raised.value.message


def test_two_entries_may_both_resolve_to_an_entry_that_resolves_to_itself() -> None:
    """The permitted shape the check must not catch by accident.

    An entry named `product` that names no target *is* `product`, so pointing at
    it is pointing at a leaf. Only a target that resolves onward is a chain.
    """
    lexicon = Lexicon.from_dict(
        lexicon_document(
            "de-DE",
            product=entry("artikel"),
            movie=entry("film", canonicalId="product"),
        )
    )

    assert lexicon.entries["movie"].canonical_id == "product"


def test_a_collision_between_two_entries_names_both_and_the_entities_they_mean() -> (
    None
):
    """The rule is unchanged; what it says is not.

    Two entries claiming one word is still refused — which filter applies is
    unanswerable. But an author reading "entity 'movie' already claims it" cannot
    see *which pair* collided when both resolve to `product`, so the message names
    each entry and the entity it resolves to.
    """
    with pytest.raises(ValidationError) as raised:
        Lexicon.from_dict(
            lexicon_document(
                "de-DE",
                movie=entry("film", canonicalId="product"),
                series=entry("film", canonicalId="product"),
            )
        )

    message = raised.value.message
    assert "movie" in message
    assert "series" in message
    assert message.count("product") == 2


def test_a_collision_between_two_plain_entries_does_not_say_it_twice() -> None:
    """An entry that resolves to itself has one name, so the message uses one.

    Naming a target that is the entry ID again would make every ambiguity error
    in every lexicon that never uses the feature read as though something more
    complicated were going on.
    """
    with pytest.raises(ValidationError) as raised:
        Lexicon.from_dict(
            lexicon_document("de-DE", product=entry("film"), invoice=entry("film"))
        )

    message = raised.value.message
    assert "resolving to" not in message
    assert "product" in message
    assert "invoice" in message


@pytest.mark.parametrize("identifier", ["product type", "produkt!", "", "prod/uct"])
def test_an_entry_key_outside_the_identifier_grammar_is_rejected(
    identifier: str,
) -> None:
    """Core accepted any string as a key, which was looser than the schema.

    An author validating offline would be told their key is wrong; core would
    load it anyway. Same grammar, same verdict, both sides.
    """
    with pytest.raises(ValidationError) as raised:
        Lexicon.from_dict(lexicon_document("de-DE", entities={identifier: entry()}))

    assert identifier in raised.value.message
    assert raised.value.field == "entities"


@pytest.mark.parametrize("identifier", ["product type", "produkt!", "", "prod/uct"])
def test_a_canonical_id_outside_the_identifier_grammar_is_rejected(
    identifier: str,
) -> None:
    """The target obeys the grammar the key obeys — it names the same kind of thing."""
    with pytest.raises(ValidationError) as raised:
        Lexicon.from_dict(
            lexicon_document("de-DE", movie=entry(canonicalId=identifier))
        )

    assert identifier in raised.value.message
    assert raised.value.canonical_id == "movie"
    assert raised.value.field == "canonicalId"
