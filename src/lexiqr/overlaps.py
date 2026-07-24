"""Choosing between hits that claim the same text, and ordering what survives.

The scan is deliberately greedy: it reports "support ticket" and the "ticket"
inside it, because it cannot know which one the tenant meant. The fuzzy pass
adds near-misses on top. Something has to decide between all of them, and the
decision is observable — a caller who snapshot-tests a report depends on it — so
it is made by one total rule rather than by whichever hit a stage happened to
emit first. This is that one rule, owning precedence for both kinds:

0. **An exact hit beats an overlapping fuzzy one**, whatever their spans. A word
   the user spelled correctly is never displaced by a guess about a word they
   didn't. Kind is asked before anything about the text.
1. **The longest span wins.** A tenant who wrote a precise multi-word label
   meant that label, not the shorter ones it happens to contain.
2. **Then the better tier wins.** Their own vocabulary beats a synonym, and a
   synonym beats the identifier they never see.
3. **Then the earlier start wins.**
4. **Then the lower canonical ID wins.** Two *different* entities can declare
   surface forms that fold to the same text — "cafe" and "café" both fold to
   "cafe" — and claim the same span at the same tier, which leaves nothing about
   the text to choose between them. Something still has to be picked, and picked
   the same way on every machine.

Rule 4 is arbitrary in the way a tiebreak has to be. Rules 0–3 are not. (Two
forms of the *same* entity that fold alike never reach here: the index keeps the
first-declared one, so only one candidate is ever emitted for them.)
"""

from __future__ import annotations

from dataclasses import dataclass

from lexiqr.types import ScoreTier

#: Best first. The enum orders by declaration, but that is a fact about the
#: enum; the ranking matching depends on is stated here.
_TIER_RANK = {
    ScoreTier.PREFERRED: 0,
    ScoreTier.ALTERNATE: 1,
    ScoreTier.CANONICAL: 2,
}


@dataclass(frozen=True)
class Candidate:
    """A hit competing for text, of either kind, in normalized coordinates.

    `is_fuzzy` is the only thing that distinguishes the two stages here; every
    other field means the same whether the hit was scanned exactly or recovered
    from a typo. The matcher translates the survivors back to the prompt.
    """

    canonical_id: str
    surface_form: str
    span: tuple[int, int]
    score_tier: ScoreTier
    is_fuzzy: bool


def resolve(candidates: tuple[Candidate, ...]) -> tuple[Candidate, ...]:
    """Drop the hits that lose an overlap, and order the rest by position."""
    kept: list[Candidate] = []
    for candidate in sorted(candidates, key=_precedence):
        if not any(_overlap(candidate, chosen) for chosen in kept):
            kept.append(candidate)
    return tuple(sorted(kept, key=lambda candidate: candidate.span))


def _precedence(candidate: Candidate) -> tuple[bool, int, int, int, str]:
    """Sort key putting the hit that should win an overlap first."""
    start, end = candidate.span
    return (
        candidate.is_fuzzy,
        start - end,
        _TIER_RANK[candidate.score_tier],
        start,
        candidate.canonical_id,
    )


def _overlap(one: Candidate, other: Candidate) -> bool:
    return one.span[0] < other.span[1] and other.span[0] < one.span[1]
