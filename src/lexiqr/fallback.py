"""Building the locale fallback chain: the order `transform()` walks locales in.

A caller states one locale. The lexicon may not declare surface forms for it,
yet declare them for a sibling variant of the same language — `de-DE` forms a
`de-AT` prompt would match perfectly. The fallback chain is the ordered list of
locales to try for a given request, and this module is the whole policy that
builds it: the exact locale first, then that language's other variants the
lexicon actually contains, then the declared default.

It is pure and I/O-free on purpose. The policy can change — later variants of
lexiqr add caller-supplied overrides on top of the declared-default backstop —
without any of that reasoning leaking into the matching pipeline, and without a
test of the policy having to run a scan. It is also only policy: what a tag is,
when two tags name one locale, and which language a tag belongs to are questions
`lexiqr.locale` answers, so the order below reads as the rule it encodes rather
than as string handling.
"""

from __future__ import annotations

from collections.abc import Iterable

from lexiqr.errors import ValidationError
from lexiqr.locale import DeclaredLocales, deduplicate


def build_chain(
    requested: str, available: Iterable[str], default_locale: str
) -> tuple[str, ...]:
    """The locales to try for `requested`, best first, filtered to `available`.

    `available` is the set of locales the lexicon declares and `default_locale`
    its declared default. The chain is the exact requested locale (only if the
    lexicon has it), then its same-language siblings, then the declared default
    as a final backstop — deduplicated, so a locale already earlier in the chain
    (the default is often the requested locale itself) is never walked twice. A
    default the lexicon does not actually author is dropped, as any absent locale
    is; a request whose language has no variant and whose default is unauthored
    yields an empty chain — the caller reads that as "no locale to try", an
    ordinary outcome rather than an error.

    Sibling variants are walked in **ascending order of their tag**, compared
    case-insensitively — so `de-AT` before `de-CH` before `de-DE`. That rule is
    total (deduplication leaves the tags distinct, so no two ever compare equal)
    and independent of the order the lexicon declared its locales in, which is
    what makes the same prompt resolve through the same variant on every run and
    platform. Because the walk stops at the first match, this order decides which
    variant answers when more than one could; the exact requested locale leading
    the chain is why authoring a variant later makes it answer its own prompts.

    Tags in the returned chain carry the lexicon's own spelling, so a caller can
    report which locale answered in the casing the lexicon author wrote.
    """
    declared = DeclaredLocales(available)
    return deduplicate(
        [
            declared.spelling_of(requested),
            *declared.variants_of(requested),
            declared.spelling_of(default_locale),
        ]
    )


def resolve_explicit_chain(
    chain: Iterable[str], available: Iterable[str]
) -> tuple[str, ...]:
    """A caller's own chain, filtered to the lexicon and validated at build time.

    An explicit chain fully replaces the default policy: the locales named here,
    in this order, are the only ones walked — a caller who wants the declared
    default as a backstop names it. Entries the lexicon does not declare are
    dropped silently, since a partially-populated lexicon is normal; the
    surviving tags carry the lexicon's own spelling. A chain that is empty, or
    empty once absent locales are dropped, could never resolve any prompt, so it
    is rejected here — at construction — rather than left to fail per request.
    """
    declared = DeclaredLocales(available)
    resolved = deduplicate(declared.spelling_of(tag) for tag in chain)

    if not resolved:
        raise ValidationError(
            "The explicit fallback chain names no locale the lexicon declares; "
            "once locales the lexicon does not contain are dropped it is empty, "
            "so no prompt could ever resolve. Name at least one locale the "
            "lexicon actually declares.",
            field="fallback_chain",
        )
    return resolved
