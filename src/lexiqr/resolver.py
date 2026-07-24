"""The `EntityResolver` facade — the only public entry point into lexiqr."""

from __future__ import annotations

from collections.abc import Iterable
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

    def __init__(
        self,
        lexicon: Lexicon,
        *,
        fuzzy: bool = True,
        fallback_chain: Iterable[str] | None = None,
    ) -> None:
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

        `fallback_chain` is an optional explicit locale chain that fully replaces
        the default policy: only the locales named here (and present in the
        lexicon), in this order, are walked. It is resolved and validated now, at
        construction — a chain that is empty, or empty once absent locales are
        dropped, raises `ValidationError` here rather than mid-request. Omitting
        it leaves the default policy — exact locale, same-language variants, then
        the declared default — in place.
        """
        self._lexicon = lexicon
        self._fuzzy = fuzzy
        self._available = _declared_locales(lexicon)
        self._indexes = {
            locale.casefold(): SurfaceFormIndex.build(lexicon, locale)
            for locale in self._available
        }
        self._explicit_chain = (
            fallback.resolve_explicit_chain(fallback_chain, self._available)
            if fallback_chain is not None
            else None
        )

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        *,
        fuzzy: bool = True,
        fallback_chain: Iterable[str] | None = None,
    ) -> EntityResolver:
        """Build a resolver from a lexicon JSON file."""
        return cls(Lexicon.from_file(path), fuzzy=fuzzy, fallback_chain=fallback_chain)

    @classmethod
    def from_dict(
        cls,
        document: dict[str, Any],
        *,
        fuzzy: bool = True,
        fallback_chain: Iterable[str] | None = None,
    ) -> EntityResolver:
        """Build a resolver from an already-parsed lexicon document."""
        return cls(
            Lexicon.from_dict(document), fuzzy=fuzzy, fallback_chain=fallback_chain
        )

    def transform(self, prompt: str, locale: str) -> MatchReport:
        """Resolve the jargon in `prompt`, read in `locale`, to canonical entities.

        Absent an explicit chain, the requested locale is tried first; if it
        produces no match, the walk continues through its same-language sibling
        variants and then the declared default. An explicit chain replaces that
        policy with the fixed, pre-validated locale list configured at
        construction. Either way the walk stops at the first locale that produces
        any match — so every match in the report comes from one locale, and the
        report names it. When no locale in the chain matches, the report's
        resolved locale is the requested one and its match list is empty, an
        ordinary result rather than an error.
        """
        chain = (
            self._explicit_chain
            if self._explicit_chain is not None
            else fallback.build_chain(
                locale, self._available, self._lexicon.default_locale
            )
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
