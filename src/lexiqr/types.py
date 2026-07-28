"""The typed result shapes of `transform()` — public API, semver-governed (ADR 0002)."""

from dataclasses import dataclass, field
from enum import Enum

from lexiqr.metadata import EMPTY, Metadata


class ScoreTier(str, Enum):
    """Deterministic ranking of match quality: preferred > alternate > canonical."""

    PREFERRED = "preferred"
    ALTERNATE = "alternate"
    CANONICAL = "canonical"


@dataclass(frozen=True)
class EntityMatch:
    """One resolution inside a match report.

    Every field ADR 0002 names is present. A match always knows which tier it
    scored in and which locale produced it, so neither is optional. `correction`
    stays `None` when the match was found by exact spelling.

    `canonical_id` means what it always meant: the entity a backend queries.
    `entry_id` names the entry that answered — the tenant's own way in — and is
    **always a real string**, equal to the canonical ID for an entry that resolves
    to itself, rather than an optional meaning "same as the canonical ID". That is
    what puts it positionally ahead of `correction`: an optional would force
    serialization to emit a null or to invent a value on read, and either breaks
    the exact round-trip guarantee. A caller debugging a wrong filter reads this
    field instead of guessing which of several entries answered.

    `metadata` is the entry's filter, carried verbatim and never interpreted. It is
    an **empty mapping rather than absent** when the entry declares none, so
    consuming code needs no guard, and it is immutable, so a caller cannot corrupt
    lexicon-derived data by mutating a match they were handed.
    """

    canonical_id: str
    entry_id: str
    surface_form: str
    span: tuple[int, int]
    score_tier: ScoreTier
    matched_locale: str
    correction: str | None = None
    metadata: Metadata = EMPTY


@dataclass(frozen=True)
class MatchReport:
    """The self-describing result of `transform()`."""

    prompt: str
    locale: str
    matches: tuple[EntityMatch, ...] = field(default_factory=tuple)
