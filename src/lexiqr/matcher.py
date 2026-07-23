"""The lexicon scan: prompt + surface forms → entity matches with spans.

Finding the occurrences belongs to the surface-form index and the fuzzy pass;
this module is the boundary where their coordinates change. Both work in
normalized text, because that is the only text their patterns were folded to
fit. A caller works in the prompt they typed. Every hit — exact or fuzzy —
crosses that line exactly once, here, and a fuzzy hit picks up its correction
in the same crossing: the original words its span points at.
"""

from __future__ import annotations

from lexiqr import fuzzy
from lexiqr.index import SurfaceFormIndex
from lexiqr.lexicon import Lexicon
from lexiqr.normalizer import Normalized, normalize
from lexiqr.overlaps import resolve
from lexiqr.types import EntityMatch


def scan(prompt: str, lexicon: Lexicon, locale: str) -> tuple[EntityMatch, ...]:
    """Resolve `prompt`, read in `locale`: exact scan, then fuzzy over the rest."""
    normalized = normalize(prompt, locale)
    index = SurfaceFormIndex.build(lexicon, locale)

    exact = resolve(index.scan(normalized.text))
    covered = tuple(hit.span for hit in exact)
    fuzzy_hits = fuzzy.scan(normalized, covered, index)

    matches = [
        EntityMatch(
            canonical_id=hit.canonical_id,
            surface_form=hit.surface_form,
            span=normalized.to_original_span(*hit.span),
            score_tier=hit.score_tier,
            matched_locale=locale,
        )
        for hit in exact
    ] + [
        _fuzzy_match(hit, normalized, prompt, locale) for hit in fuzzy_hits
    ]
    return tuple(sorted(matches, key=lambda match: match.span))


def _fuzzy_match(
    hit: fuzzy.FuzzyHit, normalized: Normalized, prompt: str, locale: str
) -> EntityMatch:
    """Build a fuzzy match, its correction naming what the user actually typed."""
    start, end = normalized.to_original_span(*hit.span)
    return EntityMatch(
        canonical_id=hit.canonical_id,
        surface_form=hit.surface_form,
        span=(start, end),
        score_tier=hit.score_tier,
        matched_locale=locale,
        correction=prompt[start:end],
    )
