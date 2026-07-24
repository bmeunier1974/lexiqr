"""Building the locale fallback chain: the order `transform()` walks locales in.

A caller states one locale. The lexicon may not declare surface forms for it,
yet declare them for a sibling variant of the same language — `de-DE` forms a
`de-AT` prompt would match perfectly. The fallback chain is the ordered list of
locales to try for a given request, and this module is the whole policy that
builds it: the exact locale first, then that language's other variants the
lexicon actually contains.

It is pure and I/O-free on purpose. The policy can change — later variants of
lexiqr add a declared-default backstop and caller-supplied overrides — without
any of that reasoning leaking into the matching pipeline, and without a test of
the policy having to run a scan. BCP 47 tags are treated as opaque identifiers:
compared case-insensitively, with only the leading language subtag extracted to
group variants. No locale database, no canonicalization, no language detection.
"""

from __future__ import annotations

from collections.abc import Iterable


def build_chain(
    requested: str, available: Iterable[str], default_locale: str
) -> tuple[str, ...]:
    """The locales to try for `requested`, best first, filtered to `available`.

    `available` is the set of locales the lexicon declares and `default_locale`
    its declared default. The chain is the exact requested locale (only if the
    lexicon has it), then its same-language siblings in a deterministic order,
    then the declared default as a final backstop — deduplicated, so a locale
    already earlier in the chain (the default is often the requested locale
    itself) is never walked twice. A default the lexicon does not actually
    author is dropped, as any absent locale is; a request whose language has no
    variant and whose default is unauthored yields an empty chain — the caller
    reads that as "no locale to try", an ordinary outcome rather than an error.

    Tags in the returned chain carry the lexicon's own spelling, so a caller can
    report which locale answered in the casing the lexicon author wrote.
    """
    # Case-insensitive lookup that remembers the lexicon's own spelling, so a
    # match reports the locale as the author wrote it, not as the caller typed.
    by_fold: dict[str, str] = {}
    for locale in available:
        by_fold.setdefault(locale.casefold(), locale)

    language = _language_subtag(requested)
    chain: list[str] = []
    seen: set[str] = set()

    def append(locale: str | None) -> None:
        if locale is not None and locale.casefold() not in seen:
            seen.add(locale.casefold())
            chain.append(locale)

    append(by_fold.get(requested.casefold()))
    for sibling in sorted(by_fold.values(), key=str.casefold):
        if _language_subtag(sibling) == language:
            append(sibling)
    append(by_fold.get(default_locale.casefold()))

    return tuple(chain)


def _language_subtag(locale: str) -> str:
    """The leading BCP 47 language subtag, casefolded — `de` for `de-AT`."""
    return locale.split("-", 1)[0].casefold()
