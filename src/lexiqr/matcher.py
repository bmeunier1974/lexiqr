"""The lexicon scan: prompt + surface forms → entity matches with spans.

Seed of the normalize → lexicon scan → fuzzy pass pipeline. The stages exist
here as seams, not as features: normalization is casefolding only, and there
is no fuzzy pass yet.
"""

from __future__ import annotations

import re

from lexiqr.lexicon import Lexicon, SurfaceForms
from lexiqr.types import EntityMatch, ScoreTier


def scan(prompt: str, lexicon: Lexicon, locale: str) -> tuple[EntityMatch, ...]:
    """Find every exact occurrence of a surface form of `locale` in `prompt`."""
    matches = [
        match
        for canonical_id, locales in lexicon.entities.items()
        if (forms := locales.get(locale)) is not None
        for match in _scan_entity(prompt, canonical_id, forms, locale)
    ]
    return tuple(sorted(matches, key=lambda match: match.span))


def _scan_entity(
    prompt: str,
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
        for span in _spans(prompt, surface_form)
    ]


def _tiered_surface_forms(forms: SurfaceForms) -> list[tuple[str, ScoreTier]]:
    tiered = [(forms.preferred_singular, ScoreTier.PREFERRED)]
    if forms.preferred_plural is not None:
        tiered.append((forms.preferred_plural, ScoreTier.PREFERRED))
    tiered.extend((alternate, ScoreTier.ALTERNATE) for alternate in forms.alternates)
    return tiered


def _spans(prompt: str, surface_form: str) -> list[tuple[int, int]]:
    """Whole-word occurrences of `surface_form`, as offsets into the original prompt."""
    pattern = rf"(?<!\w){re.escape(_normalize(surface_form))}(?!\w)"
    return [
        (found.start(), found.end())
        for found in re.finditer(pattern, _normalize(prompt))
    ]


def _normalize(text: str) -> str:
    """Trivial casing pass — accent stripping and script rules land with fuzzy matching.

    Spans are offsets into the *original* prompt, which holds while normalization
    is length-preserving. The few casefoldings that are not (e.g. "ß" → "ss") need
    the offset map the normalization plan introduces.
    """
    return text.casefold()
