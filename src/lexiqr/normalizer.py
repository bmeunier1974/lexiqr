"""Folding a prompt into a comparable form, without losing the way back.

Matching wants "épisodes" and "episodes" to be the same string. Callers want
spans that index the prompt their user actually typed. Those two wants are in
direct conflict: folding changes the text, and it does not change it evenly —
`é` decomposes to two characters and then loses one, `ß` casefolds into two.
Any offset computed against the folded text is wrong against the original by an
amount that varies along the string.

So this module is the only place that folds, and it never folds without
recording the correspondence. `Normalized` carries the folded text together
with the original index every folded character came from, and translates spans
back on request. Downstream code matches against `.text` and reports
`.to_original_span(...)`; nothing else in core has to know that folding
happened at all.

The script policy lives here too, for the same reason: what counts as a
discardable accent is a question about writing systems, not about matching.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Normalized:
    """Folded text, plus the original index each of its characters came from."""

    text: str
    #: `origins[i]` is the index in the original text that `text[i]` was folded
    #: from. Several folded characters can share an origin (`ß` → `ss`), and an
    #: original character can appear here not at all (a stripped accent).
    origins: tuple[int, ...]

    def to_original_span(self, start: int, end: int) -> tuple[int, int]:
        """Translate a span in the folded text back to the original text."""
        if start >= end:
            raise ValueError(f"span ({start}, {end}) is empty or inverted")
        return (self.origins[start], self.origins[end - 1] + 1)


def normalize(text: str, locale: str) -> Normalized:
    """Fold `text` for matching under the script policy of `locale`."""
    folded: list[str] = []
    origins: list[int] = []
    for index, character in enumerate(text):
        for character_folded in _fold_character(character, locale):
            folded.append(character_folded)
            origins.append(index)
    return Normalized(text="".join(folded), origins=tuple(origins))


def normalize_text(text: str, locale: str) -> str:
    """Fold `text` when only the folded form is wanted — a surface form, say."""
    return normalize(text, locale).text


def _fold_character(character: str, locale: str) -> str:
    """Fold one character, which may yield several characters or none at all."""
    decomposed = unicodedata.normalize("NFKD", character)
    stripped = "".join(part for part in decomposed if not unicodedata.combining(part))
    return stripped.casefold()
