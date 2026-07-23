"""The typed result shapes of `transform()` — public API, semver-governed (ADR 0002)."""

from dataclasses import dataclass, field
from enum import Enum


class ScoreTier(str, Enum):
    """Deterministic ranking of match quality: preferred > alternate > canonical."""

    PREFERRED = "preferred"
    ALTERNATE = "alternate"
    CANONICAL = "canonical"


@dataclass(frozen=True)
class EntityMatch:
    """One resolution inside a match report.

    `score_tier`, `correction` and `matched_locale` carry their not-applicable
    defaults until the plans that populate them land.
    """

    canonical_id: str
    surface_form: str
    span: tuple[int, int]
    score_tier: ScoreTier | None = None
    correction: str | None = None
    matched_locale: str | None = None


@dataclass(frozen=True)
class MatchReport:
    """The self-describing result of `transform()`."""

    prompt: str
    locale: str
    matches: tuple[EntityMatch, ...] = field(default_factory=tuple)
