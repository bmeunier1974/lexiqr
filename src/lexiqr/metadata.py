"""An entry's filter: a tenant-defined bag lexiqr carries and never interprets.

A lexicon author writing "movie" and "series" as two entries of one `product`
needs somewhere to say *which* product each one means. That is what metadata is:
`{"productType": "Movie"}` against `{"productType": "Series"}`, authored by the
tenant, carried verbatim onto every match the entry produces, and read only by
the consuming service that turns it into a query. lexiqr never looks inside a
value; what `productType = Movie` means to a search backend is not its business.

Carrying data it does not interpret is exactly why the type is bounded and closed
rather than "whatever JSON the author wrote". Everything lexiqr promises is a
bound: results are immutable, hashable, and identical across runs, and a bag of
arbitrary depth would put all three at the mercy of a tenant's file. So the domain
is a scalar or a set of scalars — no `null`, because an absent key already means
absent, and no nesting, because nesting invites a query language that is a stated
non-goal — and the module owns that domain, its limits, its immutability, its
hash, and its ordering in one place.

It knows nothing of lexicons, indexes or resolvers: a declaration goes in, a
`Metadata` or a `MetadataFault` comes out. The fault says *what* is wrong and
names the key; where in the document it happened belongs to the loader, which is
the only thing that knows.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from typing import Any

from lexiqr.errors import kind

#: What a filter value may be: a scalar, or a set of scalars. A list is in the
#: domain because a genuinely multi-valued filter — `genre` — would otherwise have
#: to be smuggled through a delimited string nobody parses. It is a tuple rather
#: than a list because a value a caller is handed must not be mutable.
MetadataValue = str | int | float | bool | tuple[str, ...]

#: The bounds, mirroring the published schema's `metadata` subschema so both sides
#: of the ADR 0003 contract give the same verdict. They are generous for any real
#: filter and small enough that a tenant's file cannot make a match report
#: expensive to hold, hash, or serialize.
MAX_KEYS = 16
MAX_KEY_LENGTH = 64
MAX_VALUE_LENGTH = 128
MAX_LIST_LENGTH = 16

#: A filter key: the same identifier grammar the format uses everywhere else,
#: bounded above because a key is carried on every match the entry produces.
_KEY = re.compile(rf"^[A-Za-z0-9_.-]{{1,{MAX_KEY_LENGTH}}}$")


class MetadataFault(Exception):
    """A declaration outside the value domain: what is wrong, and which key.

    Deliberately not a `ValidationError`. That type's contract is that it names
    where in the document the fault is, and this module cannot know — it was
    handed a bag, not a lexicon. The loader catches this and re-raises with the
    entry it came from, so one message reads with one voice.
    """

    def __init__(self, field: str, reason: str) -> None:
        self.field = field
        self.reason = reason
        super().__init__(f"field {field!r} {reason}")


class Metadata(Mapping[str, MetadataValue]):
    """One entry's filter: an immutable, hashable mapping in sorted key order.

    A `Mapping` and nothing more, so there is no method to mutate it: lexicon-
    derived data handed to a caller cannot be corrupted by the caller. Hashable,
    so a match carrying one stays usable as a dict key or set member. Iterated in
    sorted key order, so anything built from it — a canonical serialization, a
    rendered line, a debug print — is stable across runs and platforms without the
    caller having to sort.
    """

    __slots__ = ("_items",)

    def __init__(self, items: Mapping[str, MetadataValue] | None = None) -> None:
        """Hold `items` sorted by key. Prefer `Metadata.of` for a declaration.

        The constructor trusts what it is given; `of` is where a tenant's document
        is checked. Sorting happens once, here, so every read is already in order.
        """
        self._items: tuple[tuple[str, MetadataValue], ...] = tuple(
            sorted((items or {}).items())
        )

    @classmethod
    def of(cls, declared: Any) -> Metadata:
        """The filter a document declared, checked against the value domain.

        `None` — the field absent — is the empty filter, not an error: most
        entries carry none. An empty *object* is an error, because writing
        `"metadata": {}` says something the author did not mean.
        """
        if declared is None:
            return EMPTY
        if not isinstance(declared, dict):
            raise MetadataFault("metadata", f"must be an object, not {kind(declared)}")
        if not declared:
            raise MetadataFault(
                "metadata", "is empty; omit it rather than declaring no filter"
            )
        if len(declared) > MAX_KEYS:
            raise MetadataFault(
                "metadata",
                f"declares {len(declared)} keys, which exceeds the maximum of "
                f"{MAX_KEYS}",
            )
        return cls({key: _value(key, declared[key]) for key in map(_key, declared)})

    def __getitem__(self, key: str) -> MetadataValue:
        # A linear scan over at most `MAX_KEYS` pairs, which is why one sorted
        # tuple can be the whole state: no second index to keep in step with it.
        for held, value in self._items:
            if held == key:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (key for key, _ in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __hash__(self) -> int:
        return hash(self._items)

    def __repr__(self) -> str:
        return f"Metadata({dict(self._items)!r})"


#: The filter of an entry that declares none. One shared instance, because it
#: holds nothing and is immutable, so every match without a filter can point at
#: the same object rather than allocate an empty one.
EMPTY = Metadata()


def _key(key: Any) -> str:
    """`key` as a well-formed filter key, or a fault naming it."""
    if not isinstance(key, str) or not _KEY.fullmatch(key):
        raise MetadataFault(
            "metadata",
            f"has key {key!r}, which is not a well-formed filter key (letters, "
            f"digits, '_', '.' and '-', up to {MAX_KEY_LENGTH} characters)",
        )
    return key


def _value(key: str, value: Any) -> MetadataValue:
    """`value` as a filter value, or a fault naming the key it was declared under.

    Booleans are asked about before numbers because `bool` is a subclass of `int`
    in Python: without that order, `True` would be read as the number 1 and a
    tenant's flag would come back as an integer.
    """
    field = f"metadata.{key}"
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        return _scalar(field, value)
    if isinstance(value, list):
        return _list(field, value)
    raise MetadataFault(
        field,
        f"is {kind(value)}; a filter value must be a string, a number, a "
        f"boolean, or a list of strings",
    )


def _scalar(field: str, value: str) -> str:
    if not value:
        raise MetadataFault(field, "is empty; a filter nobody set is not a filter")
    # Beyond the schema, whose minLength cannot tell a value from a blank one —
    # the same reason a surface form may not be whitespace (see
    # docs/lexicon-semantic-checks.md). An accidental run of spaces must not
    # become a live filter that silently narrows every query.
    if not value.strip():
        raise MetadataFault(
            field,
            f"is {value!r}, which is only whitespace; that is not a filter a "
            f"backend can act on",
        )
    if len(value) > MAX_VALUE_LENGTH:
        raise MetadataFault(
            field,
            f"is {len(value)} characters long, which exceeds the maximum filter "
            f"value length of {MAX_VALUE_LENGTH}",
        )
    return value


def _list(field: str, value: list[Any]) -> tuple[str, ...]:
    if not value:
        raise MetadataFault(field, "is an empty list; omit the key instead")
    if len(value) > MAX_LIST_LENGTH:
        raise MetadataFault(
            field,
            f"holds {len(value)} values, which exceeds the maximum of "
            f"{MAX_LIST_LENGTH}",
        )
    items = tuple(_scalar(field, _string(field, item)) for item in value)
    if len(set(items)) != len(items):
        raise MetadataFault(field, "repeats a value; a set of filters is a set")
    return items


def _string(field: str, item: Any) -> str:
    if not isinstance(item, str):
        raise MetadataFault(
            field, f"holds {kind(item)}; a list filter value holds strings only"
        )
    return item
