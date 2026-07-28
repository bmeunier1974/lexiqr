"""The `EntityResolver` facade — the only public entry point into lexiqr.

Being the only entry point makes this the only place input can be refused, so
deciding what lexiqr accepts is `transform()`'s own first act rather than a
stage behind it: the pipeline it feeds (normalize, scan, fuzzy) never has to
defend itself against hostile input, and "what is acceptable" is read, tested,
and changed where it is enforced.

The two decisions are deliberately different in kind, and reading them together
at the top of `transform()` is the point. Exceeding the documented size limit is
a *failure* — it raises `ValidationError`, before any matching work, so hostile
input costs a rejection rather than a full pipeline pass. Empty or
whitespace-only input is a *result* — "the user typed nothing" is an ordinary
outcome, so it resolves to an empty match report.

Accepted text is passed on *unchanged*: acceptance bounds and refuses, it never
mangles, so the spans a report carries keep indexing the prompt the user
actually typed. Adversarial Unicode follows from that. The size limit already
bounds what a combining-character flood, bidi-control run, or astral-plane blob
can cost, and since nothing is sanitized on the way in, those resolve
predictably rather than distorting what matches. The one class refused outright
is a lone surrogate: a malformed code point that cannot be encoded to UTF-8, and
so must fail at the boundary rather than propagate into a report that could
never be serialized.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from lexiqr import fallback
from lexiqr.errors import ValidationError
from lexiqr.index import SurfaceFormIndex
from lexiqr.lexicon import Lexicon
from lexiqr.locale import deduplicate, fold
from lexiqr.matcher import scan
from lexiqr.types import MatchReport

#: The maximum prompt length lexiqr accepts, in Unicode code points. This is a
#: documented part of the contract, not a per-call argument or a configuration
#: knob: one number every integrating developer can reason about, stated in the
#: README and exported from the package root. Changing it is a semver-visible
#: change. It is set well below the size at which a pasted document would
#: threaten a request thread, so a prompt that exceeds it is rejected cheaply
#: rather than scanned.
MAX_PROMPT_LENGTH = 10_000

#: A lone surrogate — any code point in U+D800..U+DFFF standing on its own. A
#: well-formed Python `str` never holds a *paired* surrogate (astral characters
#: are single code points), so a surrogate found here is always malformed: it
#: cannot be encoded to UTF-8, which means it could never be serialized, stored,
#: or round-tripped. It is refused at the boundary rather than allowed to reach
#: a report that downstream code then cannot handle.
_LONE_SURROGATE = re.compile("[\ud800-\udfff]")


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
            fold(locale): SurfaceFormIndex.build(lexicon, locale)
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

        Before any of that, the prompt has to be acceptable. One past the
        documented maximum length, or carrying a malformed code point, is
        rejected here with a `ValidationError` — ahead of normalization and
        matching, so hostile input costs a rejection rather than a full pipeline
        pass. Empty or whitespace-only input is the other bounded case: "the
        user typed nothing" is an ordinary result, so it resolves to an empty
        report without touching the pipeline. Whitespace is judged by
        `str.strip()`, which covers spaces, tabs, newlines, and Unicode
        whitespace alike, so a caller never has to pre-trim.
        """
        _reject_unacceptable_prompt(prompt)
        if not prompt.strip():
            return MatchReport(prompt=prompt, locale=locale, matches=())
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
                self._indexes[fold(chain_locale)],
                chain_locale,
                fuzzy_enabled=self._fuzzy,
            )
            if matches:
                return MatchReport(prompt=prompt, locale=chain_locale, matches=matches)
        return MatchReport(prompt=prompt, locale=locale, matches=())


def _reject_unacceptable_prompt(prompt: str) -> None:
    """Raise `ValidationError` if `prompt` is too long or malformed; else return.

    Length is counted in code points, so the verdict does not depend on the
    platform's or interpreter's internal string representation.
    """
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise ValidationError(
            f"Prompt exceeds the maximum length of {MAX_PROMPT_LENGTH} "
            f"characters (got {len(prompt)}).",
            field="prompt",
        )
    surrogate = _LONE_SURROGATE.search(prompt)
    if surrogate is not None:
        raise ValidationError(
            f"Prompt contains a lone surrogate (U+{ord(surrogate.group()):04X}) at "
            f"position {surrogate.start()}; such malformed code points cannot be "
            f"encoded and are rejected at the input boundary.",
            field="prompt",
        )


def _declared_locales(lexicon: Lexicon) -> tuple[str, ...]:
    """Every locale the lexicon declares, once each, in first-seen order.

    Comparison is case-insensitive — a tag is an opaque identifier — so the
    first spelling encountered stands in for any later case variant of it.
    """
    return deduplicate(
        locale for locales in lexicon.entities.values() for locale in locales
    )
