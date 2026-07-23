"""The lexicon scan: prompt + surface forms → entity matches with spans.

Finding the occurrences belongs to the surface-form index; this module is the
boundary where their coordinates change. The index works in normalized text,
because that is the only text its patterns were folded to fit. A caller works
in the prompt they typed. Every hit crosses that line exactly once, here.
"""

from __future__ import annotations

from lexiqr.index import SurfaceFormIndex
from lexiqr.lexicon import Lexicon
from lexiqr.normalizer import normalize
from lexiqr.types import EntityMatch


def scan(prompt: str, lexicon: Lexicon, locale: str) -> tuple[EntityMatch, ...]:
    """Find every exact occurrence of a surface form of `locale` in `prompt`."""
    normalized = normalize(prompt, locale)
    matches = [
        EntityMatch(
            canonical_id=hit.canonical_id,
            surface_form=hit.surface_form,
            span=normalized.to_original_span(*hit.span),
            score_tier=hit.score_tier,
            matched_locale=locale,
        )
        for hit in SurfaceFormIndex.build(lexicon, locale).scan(normalized.text)
    ]
    return tuple(sorted(matches, key=lambda match: match.span))
