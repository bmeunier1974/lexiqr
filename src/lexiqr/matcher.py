"""The lexicon scan: prompt + surface forms → entity matches with spans.

Finding the occurrences belongs to the surface-form index and the fuzzy pass;
this module is the boundary where their coordinates change. Both work in
normalized text, because that is the only text their patterns were folded to
fit. A caller works in the prompt they typed. Every hit — exact or fuzzy —
crosses that line exactly once, here, and a fuzzy hit picks up its correction
in the same crossing: the original words its span points at.

The exact scan claims what it can; the fuzzy pass then looks only at the words
no exact hit touched. Both kinds meet in one overlap resolver, which owns the
precedence between them — an exact hit is never displaced by a fuzzy guess.
"""

from __future__ import annotations

from lexiqr import fuzzy
from lexiqr.index import SurfaceFormIndex
from lexiqr.normalizer import Normalized, normalize
from lexiqr.overlaps import Candidate, resolve
from lexiqr.types import EntityMatch


def scan(
    prompt: str, index: SurfaceFormIndex, locale: str, *, fuzzy_enabled: bool = True
) -> tuple[EntityMatch, ...]:
    """Resolve `prompt`, read in `locale`, against `locale`'s prebuilt index.

    The index is compiled once at resolver construction and handed in, so a
    `transform()` call — including each locale a fallback chain walks — does no
    index-building work. With `fuzzy_enabled` off the second pass is skipped
    outright, not run and filtered — exact-only mode does no fuzzy work at all.
    """
    normalized = normalize(prompt, locale)

    exact = index.scan(normalized.text)
    covered = tuple(hit.span for hit in exact)
    fuzzy_hits = fuzzy.scan(normalized, covered, index) if fuzzy_enabled else ()

    candidates = tuple(
        Candidate(
            canonical_id=hit.canonical_id,
            surface_form=hit.surface_form,
            span=hit.span,
            score_tier=hit.score_tier,
            is_fuzzy=False,
        )
        for hit in exact
    ) + tuple(
        Candidate(
            canonical_id=hit.canonical_id,
            surface_form=hit.surface_form,
            span=hit.span,
            score_tier=hit.score_tier,
            is_fuzzy=True,
        )
        for hit in fuzzy_hits
    )

    return tuple(
        _to_match(candidate, normalized, prompt, locale)
        for candidate in resolve(candidates)
    )


def _to_match(
    candidate: Candidate, normalized: Normalized, prompt: str, locale: str
) -> EntityMatch:
    """Translate a surviving candidate back to the prompt the caller typed.

    A fuzzy candidate carries a correction — the original words its span points
    at, so a highlighted span still marks what the user actually typed. An exact
    one carries none.
    """
    start, end = normalized.to_original_span(*candidate.span)
    return EntityMatch(
        canonical_id=candidate.canonical_id,
        surface_form=candidate.surface_form,
        span=(start, end),
        score_tier=candidate.score_tier,
        matched_locale=locale,
        correction=prompt[start:end] if candidate.is_fuzzy else None,
    )
