"""The `EntityResolver` facade — the only public entry point into lexiqr."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexiqr.lexicon import Lexicon
from lexiqr.types import MatchReport


class EntityResolver:
    """Resolves tenant jargon in a prompt to canonical entities.

    One instance holds one tenant's lexicon; mapping tenants to instances is
    the host application's job.
    """

    def __init__(self, lexicon: Lexicon) -> None:
        self._lexicon = lexicon

    @classmethod
    def from_file(cls, path: str | Path) -> EntityResolver:
        """Build a resolver from a lexicon JSON file."""
        return cls(Lexicon.from_file(path))

    @classmethod
    def from_dict(cls, document: dict[str, Any]) -> EntityResolver:
        """Build a resolver from an already-parsed lexicon document."""
        return cls(Lexicon.from_dict(document))

    def transform(self, prompt: str, locale: str) -> MatchReport:
        """Resolve the jargon in `prompt`, read in `locale`, to canonical entities."""
        return MatchReport(prompt=prompt, locale=locale, matches=())
