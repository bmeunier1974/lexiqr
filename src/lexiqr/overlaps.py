"""Choosing between hits that claim the same text, and ordering what survives.

The scan is deliberately greedy: it reports "support ticket" and the "ticket"
inside it, because it cannot know which one the tenant meant. Something has to
decide, and the decision is observable — a caller who snapshot-tests a report
depends on it — so it is made by one total rule rather than by whichever hit
the scan happened to emit first:

1. **The longest span wins.** A tenant who wrote a precise multi-word label
   meant that label, not the shorter ones it happens to contain.
2. **Then the better tier wins.** Their own vocabulary beats a synonym, and a
   synonym beats the identifier they never see.
3. **Then the earlier start wins.**
4. **Then the lower canonical ID wins.** Two entities can declare the same
   surface form, which leaves nothing about the *text* to choose between them.
   Something still has to be picked, and picked the same way on every machine.

Rule 4 is arbitrary in the way a tiebreak has to be. Rules 1–3 are not.
"""

from __future__ import annotations

from lexiqr.index import Hit
from lexiqr.types import ScoreTier

#: Best first. The enum orders by declaration, but that is a fact about the
#: enum; the ranking matching depends on is stated here.
_TIER_RANK = {
    ScoreTier.PREFERRED: 0,
    ScoreTier.ALTERNATE: 1,
    ScoreTier.CANONICAL: 2,
}


def resolve(hits: tuple[Hit, ...]) -> tuple[Hit, ...]:
    """Drop the hits that lose an overlap, and order the rest by position."""
    kept: list[Hit] = []
    for hit in sorted(hits, key=_precedence):
        if not any(_overlap(hit, chosen) for chosen in kept):
            kept.append(hit)
    return tuple(sorted(kept, key=lambda hit: hit.span))


def _precedence(hit: Hit) -> tuple[int, int, int, str]:
    """Sort key putting the hit that should win an overlap first."""
    start, end = hit.span
    return (start - end, _TIER_RANK[hit.score_tier], start, hit.canonical_id)


def _overlap(one: Hit, other: Hit) -> bool:
    return one.span[0] < other.span[1] and other.span[0] < one.span[1]
