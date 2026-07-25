"""BCP 47 tags — the one module that knows what a locale tag is made of.

A locale reaches lexiqr as a string, from two places that never meet: a lexicon
author writes tags as keys in a document, and an integrating developer passes
one to `transform()`. Between them, four questions get asked about that string —
is it a tag at all, are these two tags the same locale, what language is it, and
which of the locales a lexicon declares does it name. Answered locally, each
answer is one line; answered locally *four times over*, they are four chances
for the loader to accept a tag the chain then fails to find, or for the script
policy to read a subtag the fallback policy grouped differently.

So they are answered here, once. Everything lexiqr knows about the *shape* of a
tag lives in this module, and every other module asks it rather than reaching
for `casefold()` or splitting on a hyphen itself.

The knowledge is deliberately shallow, and stays that way (docs/matching-rules.md
§5): tags are opaque identifiers, compared as written and never rewritten. There
is no locale database, no canonicalisation, no alias resolution, and no language
detection. `de_DE` is not `de-DE`, because a tolerance that guesses at an
author's intent is a rule a caller cannot predict.

Internal, and not part of the public API — nothing here is exported.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

#: The subset of BCP 47 the lexicon format accepts, mirroring the published
#: schema's `$defs/locale` — language, optional script, optional region. The
#: schema and this pattern are two statements of one rule (ADR 0003), so a
#: document a schema-aware editor calls valid is one core also loads.
_WELL_FORMED = re.compile(r"[A-Za-z]{2,3}(-[A-Za-z]{4})?(-([A-Za-z]{2}|[0-9]{3}))?")


def is_well_formed(tag: str) -> bool:
    """Whether `tag` is a locale tag the lexicon format accepts.

    Well-formed, not registered: `zz-ZZ` names no real locale and passes here.
    Core validates shape so a typo is caught at load time; which locales exist
    is the author's business, not a registry lexiqr carries.
    """
    return _WELL_FORMED.fullmatch(tag) is not None


def fold(tag: str) -> str:
    """`tag` in the form two tags are compared in — `de-DE` and `DE-de` agree.

    Casefolding, and nothing else. The folded form is a comparison key, never a
    value to report or store: a matched locale is always given back in the
    spelling its author wrote.
    """
    return tag.casefold()


def language_of(tag: str) -> str:
    """The leading language subtag, folded — `de` for `de-AT`, `ar` for `AR-eg`.

    The only structure lexiqr reads out of a tag. It groups variants of one
    language for the fallback chain and selects the script policy for folding
    text; nothing else in the tag is interpreted.
    """
    return fold(tag.split("-", 1)[0])


def deduplicate(tags: Iterable[str | None]) -> tuple[str, ...]:
    """The tags in order, dropping absent ones and any locale already named.

    "Already named" is judged by `fold`, so one locale spelled two ways appears
    once — in its first spelling, at its first position. `None` stands for a
    locale that turned out not to exist, so a caller can assemble a sequence of
    lookups without filtering it first.
    """
    ordered: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        if tag is None or fold(tag) in seen:
            continue
        seen.add(fold(tag))
        ordered.append(tag)
    return tuple(ordered)


class DeclaredLocales:
    """The locales a lexicon declares, looked up the way tags compare.

    Callers hold tags from outside the lexicon — a caller's requested locale, a
    configured fallback chain — and need to know which declared locale, if any,
    each names. That question is case-insensitive, and its answer is always the
    lexicon's own spelling, so whatever a caller typed, what gets reported back
    is what the author wrote.
    """

    def __init__(self, tags: Iterable[str]) -> None:
        self._by_fold: dict[str, str] = {}
        for tag in tags:
            self._by_fold.setdefault(fold(tag), tag)

    def spelling_of(self, tag: str) -> str | None:
        """The lexicon's spelling of `tag`, or `None` if it declares no such locale."""
        return self._by_fold.get(fold(tag))

    def variants_of(self, tag: str) -> tuple[str, ...]:
        """Every declared locale of `tag`'s language, in ascending tag order.

        Ascending by folded tag — `de-AT`, `de-CH`, `de-DE` — which is a total
        order over distinct locales and owes nothing to the order the lexicon
        declared them in. That is what makes a walk over variants land on the
        same one on every run, machine, and hash seed. `tag` itself is included
        when the lexicon declares it; a caller that wants it first says so.
        """
        language = language_of(tag)
        return tuple(
            declared
            for declared in sorted(self._by_fold.values(), key=fold)
            if language_of(declared) == language
        )
