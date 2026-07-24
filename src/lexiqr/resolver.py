"""The `EntityResolver` facade — the only public entry point into lexiqr."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexiqr import fallback
from lexiqr.index import SurfaceFormIndex
from lexiqr.lexicon import Lexicon
from lexiqr.matcher import scan
from lexiqr.types import MatchReport


class EntityResolver:
    """Resolves tenant jargon in a prompt to canonical entities.

    One instance holds one tenant's lexicon; mapping tenants to instances is
    the host application's job.
    """

    def __init__(self, lexicon: Lexicon, *, fuzzy: bool = True) -> None:
        """Hold one tenant's lexicon and compile its per-locale scan indexes.

        Every locale the lexicon declares is compiled into a surface-form index
        once, here, so `transform()` — including each locale a fallback chain
        walks — never builds an index in the request path. The common case, a
        prompt in a locale the lexicon declares, costs exactly what it did
        before fallback existed: its index is looked up, not rebuilt.

        `fuzzy` is public, semver-governed API. It defaults to on, so typo
        tolerance works without configuration; passing `fuzzy=False` returns the
        resolver to exact-only behavior, skipping the fuzzy pass entirely rather
        than running and filtering it — exact-only mode is also the fast mode.
        """
        self._lexicon = lexicon
        self._fuzzy = fuzzy
        self._available = _declared_locales(lexicon)
        self._indexes = {
            locale.casefold(): SurfaceFormIndex.build(lexicon, locale)
            for locale in self._available
        }

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
        """Resolve the jargon in `prompt`, read in `locale`, to canonical entities.

        The requested locale is tried first; if it produces no match, the walk
        continues through its same-language sibling variants and stops at the
        first locale that produces any match — so every match in the report
        comes from one locale, and the report names it. When no locale in the
        chain matches, the report's resolved locale is the requested one and its
        match list is empty, an ordinary result rather than an error.
        """
        chain = fallback.build_chain(
            locale, self._available, self._lexicon.default_locale
        )
        for chain_locale in chain:
            matches = scan(
                prompt,
                self._indexes[chain_locale.casefold()],
                chain_locale,
                fuzzy_enabled=self._fuzzy,
            )
            if matches:
                return MatchReport(prompt=prompt, locale=chain_locale, matches=matches)
        return MatchReport(prompt=prompt, locale=locale, matches=())


def _declared_locales(lexicon: Lexicon) -> tuple[str, ...]:
    """Every locale the lexicon declares, once each, in first-seen order.

    Comparison is case-insensitive — a tag is an opaque identifier — so the
    first spelling encountered stands in for any later case variant of it.
    """
    seen: dict[str, str] = {}
    for locales in lexicon.entities.values():
        for locale in locales:
            seen.setdefault(locale.casefold(), locale)
    return tuple(seen.values())
