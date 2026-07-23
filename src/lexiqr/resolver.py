"""The `EntityResolver` facade — the only public entry point into lexiqr."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexiqr.lexicon import Lexicon
from lexiqr.matcher import scan
from lexiqr.types import MatchReport


class EntityResolver:
    """Resolves tenant jargon in a prompt to canonical entities.

    One instance holds one tenant's lexicon; mapping tenants to instances is
    the host application's job.
    """

    def __init__(self, lexicon: Lexicon, *, fuzzy: bool = True) -> None:
        """Hold one tenant's lexicon.

        `fuzzy` is public, semver-governed API. It defaults to on, so typo
        tolerance works without configuration; passing `fuzzy=False` returns the
        resolver to exact-only behavior, skipping the fuzzy pass entirely rather
        than running and filtering it — exact-only mode is also the fast mode.
        """
        self._lexicon = lexicon
        self._fuzzy = fuzzy

    @classmethod
    def from_file(cls, path: str | Path, *, fuzzy: bool = True) -> EntityResolver:
        """Build a resolver from a lexicon JSON file."""
        return cls(Lexicon.from_file(path), fuzzy=fuzzy)

    @classmethod
    def from_dict(
        cls, document: dict[str, Any], *, fuzzy: bool = True
    ) -> EntityResolver:
        """Build a resolver from an already-parsed lexicon document."""
        return cls(Lexicon.from_dict(document), fuzzy=fuzzy)

    def transform(self, prompt: str, locale: str) -> MatchReport:
        """Resolve the jargon in `prompt`, read in `locale`, to canonical entities."""
        return MatchReport(
            prompt=prompt,
            locale=locale,
            matches=scan(prompt, self._lexicon, locale, fuzzy_enabled=self._fuzzy),
        )
