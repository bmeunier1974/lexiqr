"""lexiqr — deterministic resolution of tenant jargon to canonical entities.

The public API is deliberately one name: everything an integrating developer
needs goes through `EntityResolver` (ADR 0002).
"""

from lexiqr.errors import ValidationError
from lexiqr.resolver import EntityResolver
from lexiqr.serialization import deserialize_report, serialize_report
from lexiqr.types import EntityMatch, MatchReport, ScoreTier

__all__ = [
    "EntityMatch",
    "EntityResolver",
    "MatchReport",
    "ScoreTier",
    "ValidationError",
    "deserialize_report",
    "serialize_report",
]
