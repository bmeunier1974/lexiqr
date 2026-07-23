"""The lexicon scan: prompt + surface forms → entity matches with spans.

The scan works entirely in normalized coordinates — it compares folded text to
folded surface forms — and translates each hit back to the original prompt
before it leaves. That translation happens once, here, at the boundary, so the
spans a caller receives are always offsets into the prompt they passed in.
"""

from __future__ import annotations

import re

from lexiqr.lexicon import Lexicon, SurfaceForms
from lexiqr.normalizer import Normalized, normalize, normalize_text
from lexiqr.types import EntityMatch, ScoreTier


def scan(prompt: str, lexicon: Lexicon, locale: str) -> tuple[EntityMatch, ...]:
    """Find every exact occurrence of a surface form of `locale` in `prompt`."""
    normalized = normalize(prompt, locale)
    matches = [
        match
        for canonical_id, locales in lexicon.entities.items()
        if (forms := locales.get(locale)) is not None
        for match in _scan_entity(normalized, canonical_id, forms, locale)
    ]
    return tuple(sorted(matches, key=lambda match: match.span))


def _scan_entity(
    normalized: Normalized,
    canonical_id: str,
    forms: SurfaceForms,
    locale: str,
) -> list[EntityMatch]:
    return [
        EntityMatch(
            canonical_id=canonical_id,
            surface_form=surface_form,
            span=span,
            score_tier=tier,
            matched_locale=locale,
        )
        for surface_form, tier in _tiered_surface_forms(forms)
        for span in _spans(normalized, surface_form, locale)
    ]


def _tiered_surface_forms(forms: SurfaceForms) -> list[tuple[str, ScoreTier]]:
    tiered = [(forms.preferred_singular, ScoreTier.PREFERRED)]
    if forms.preferred_plural is not None:
        tiered.append((forms.preferred_plural, ScoreTier.PREFERRED))
    tiered.extend((alternate, ScoreTier.ALTERNATE) for alternate in forms.alternates)
    return tiered


def _spans(
    normalized: Normalized, surface_form: str, locale: str
) -> list[tuple[int, int]]:
    """Whole-word occurrences of `surface_form`, as offsets into the original prompt."""
    folded = normalize_text(surface_form, locale)
    if not folded:
        return []
    pattern = rf"(?<!\w){re.escape(folded)}(?!\w)"
    return [
        normalized.to_original_span(found.start(), found.end())
        for found in re.finditer(pattern, normalized.text)
    ]
