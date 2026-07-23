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

    Every field ADR 0002 names is present. A match always knows which tier it
    scored in and which locale produced it, so neither is optional. `correction`
    stays `None` until the fuzzy pass (plan 004) has something to record.
    """

    canonical_id: str
    surface_form: str
    span: tuple[int, int]
    score_tier: ScoreTier
    matched_locale: str
    correction: str | None = None


@dataclass(frozen=True)
class MatchReport:
    """The self-describing result of `transform()`."""

    prompt: str
    locale: str
    matches: tuple[EntityMatch, ...] = field(default_factory=tuple)
