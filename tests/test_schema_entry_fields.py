"""What the published schema now lets an entry declare, checked offline.

A lexicon author validates with standard tooling and never installs lexiqr, so
the schema is the whole contract for the two fields that let several terms
resolve to one entity: `canonicalId`, the entity the entry resolves to, and
`metadata`, the bag that tells one entry's entity apart from another's.

The rejections live in `schema/fixtures/invalid/`, discovered and asserted by
`tests/test_lexicon_schema.py`; a bound worth having is a bound with a fixture.
What lives here is the other half — what the schema *accepts* — which cannot be
a fixture yet: `tests/test_equivalence.py` requires every schema-valid document
in the corpus to load in core, and core does not understand these fields until
the loader stories land.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from conftest import REPO_ROOT, lexicon_document

SCHEMA_PATH = REPO_ROOT / "schema" / "lexicon.v1.schema.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def validator() -> Draft202012Validator:
    return Draft202012Validator(load(SCHEMA_PATH))


def entry(**fields: Any) -> dict[str, Any]:
    """An entry declaring one German surface form, plus whatever `fields` add."""
    return {
        "locales": {"de-DE": {"preferred": {"singular": "film"}}},
        **fields,
    }


def test_an_entry_may_name_the_entity_it_resolves_to(
    validator: Draft202012Validator,
) -> None:
    """The whole point of the field: two entries, one entity in the backend.

    "movie" and "series" are what the tenant's users type; `product` is what the
    backend queries. Without this the author must invent entities their database
    does not have.
    """
    validator.validate(
        lexicon_document(
            "de-DE",
            movie=entry(canonicalId="product"),
            series=entry(canonicalId="product"),
        )
    )


def test_an_entry_may_carry_the_filter_that_tells_its_entity_apart(
    validator: Draft202012Validator,
) -> None:
    """What makes two entries resolving to one entity useful rather than lossy.

    Both are `product`; the metadata is what a consuming service reads to build
    the query that narrows to one of them.
    """
    validator.validate(
        lexicon_document(
            "de-DE",
            movie=entry(canonicalId="product", metadata={"productType": "Movie"}),
            series=entry(canonicalId="product", metadata={"productType": "Series"}),
        )
    )


def test_a_filter_value_may_be_a_scalar_or_a_set_of_scalars(
    validator: Draft202012Validator,
) -> None:
    """The value domain, pinned from the accepting side.

    A list is in the domain because a genuinely multi-valued filter — `genre` —
    would otherwise have to be smuggled through a delimited string nobody parses.
    Where the domain *ends* is pinned by the fixtures in
    `schema/fixtures/invalid/`: no null, no nesting, and every bound.
    """
    validator.validate(
        lexicon_document(
            "de-DE",
            movie=entry(
                canonicalId="product",
                metadata={
                    "productType": "Movie",
                    "minimumAge": 12,
                    "streamable": True,
                    "genre": ["drama", "thriller"],
                },
            ),
        )
    )


def test_both_fields_stay_optional_so_a_simple_lexicon_is_unchanged(
    validator: Draft202012Validator,
) -> None:
    """An entry that resolves to itself and carries no filter names neither field.

    Every lexicon written before these fields existed keeps its exact meaning,
    and no author is made to name an entity twice.
    """
    validator.validate(lexicon_document("de-DE", product=entry()))
