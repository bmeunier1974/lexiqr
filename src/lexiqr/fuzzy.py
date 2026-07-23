"""Second-pass tolerance: the residue the exact scan left, matched within budget.

Exact matching claims what it can and stops. Whatever surface form a user
misspelled it never sees, because a typo is by definition not the string the
automaton was built from. This pass picks up only from there: it looks at the
text the exact scan did *not* cover, and asks, for each leftover word, whether
it is a near-miss of some declared surface form.

It is the one place in core that reasons about edit distance and similarity.
The matcher, the resolver, and the overlap rules stay ignorant of both — they
receive fuzzy hits already decided, in the same normalized coordinates an exact
hit arrives in, and translate them at the same single boundary. That isolation
is deliberate: a tolerance regression points here and nowhere else.

Scoring is rapidfuzz, already the library's only runtime dependency: a
Damerau-Levenshtein distance, so a transposition costs one edit the way people
actually mistype, and a Jaro-Winkler similarity to rank near-misses of equal
distance. This slice matches single words against one provisional budget; the
length-aware budget table and the published similarity threshold arrive with
the next story.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz.distance import DamerauLevenshtein, JaroWinkler

from lexiqr.index import SurfaceForm, SurfaceFormIndex
from lexiqr.normalizer import Normalized
from lexiqr.types import ScoreTier

#: A candidate is a word: the same run of word characters the exact scan treats
#: as standing alone, so residue tokens line up with what it already claimed.
_WORD = re.compile(r"\w+")

#: Tolerance scales with how much evidence a surface form carries. A three-letter
#: jargon term gets no edits — otherwise it collides with every other short word
#: in the prompt and no one can explain why "cat" resolved to `product`. Four to
#: five characters earn a single edit, six or more earn two. The boundaries are
#: the branch-735 table, published in docs/matching-rules.md (story #35).
_LONG_FORM = 6
_MEDIUM_FORM = 4

#: On top of the distance budget: a candidate must also be this similar, so the
#: library never reaches for a wildly different word just because the distance
#: happened to fit. Below it, nothing matches.
_MIN_SIMILARITY = 0.90


def _edit_budget(folded_length: int) -> int:
    """The edit budget a surface form of this folded length earns."""
    if folded_length >= _LONG_FORM:
        return 2
    if folded_length >= _MEDIUM_FORM:
        return 1
    return 0

#: Best tier first, matching the overlap resolver's ranking. Used only to break
#: ties between candidates that are otherwise equally good corrections.
_TIER_RANK = {
    ScoreTier.PREFERRED: 0,
    ScoreTier.ALTERNATE: 1,
    ScoreTier.CANONICAL: 2,
}


@dataclass(frozen=True)
class FuzzyHit:
    """One near-miss the fuzzy pass is willing to stand behind.

    The span indexes the *normalized* text, exactly as an exact `Hit` does, so
    the matcher translates it back to the prompt at the one boundary it owns.
    That the hit is fuzzy — and so carries a correction — is what distinguishes
    it; the correction's text is the original words the span points at.
    """

    canonical_id: str
    surface_form: str
    span: tuple[int, int]
    score_tier: ScoreTier


def scan(
    normalized: Normalized,
    covered: tuple[tuple[int, int], ...],
    index: SurfaceFormIndex,
) -> tuple[FuzzyHit, ...]:
    """Near-miss hits over the words the exact scan left uncovered."""
    forms = _fuzzy_candidates(index.forms())
    hits: list[FuzzyHit] = []
    for token, span in _uncovered_tokens(normalized.text, covered):
        best = _best_candidate(token, forms)
        if best is not None:
            hits.append(
                FuzzyHit(
                    canonical_id=best.canonical_id,
                    surface_form=best.surface_form,
                    span=span,
                    score_tier=best.score_tier,
                )
            )
    return tuple(hits)


def _fuzzy_candidates(forms: tuple[SurfaceForm, ...]) -> tuple[SurfaceForm, ...]:
    """The declared vocabulary a typo may be tolerated against.

    The canonical ID rides along in the index as a surface form of last resort,
    so a prompt that names it outright still resolves. But it is the identifier
    the tenant never sees, and tolerating *misspellings* of it would let a user
    word drift into an internal name it never meant — so fuzzy matching reaches
    only for the tenant's own preferred and alternate labels.
    """
    return tuple(form for form in forms if form.score_tier is not ScoreTier.CANONICAL)


def _uncovered_tokens(
    text: str, covered: tuple[tuple[int, int], ...]
) -> list[tuple[str, tuple[int, int]]]:
    """The word tokens of `text` that no exact hit already claimed."""
    return [
        (match.group(), (match.start(), match.end()))
        for match in _WORD.finditer(text)
        if not any(_overlaps((match.start(), match.end()), span) for span in covered)
    ]


def _best_candidate(token: str, forms: tuple[SurfaceForm, ...]) -> SurfaceForm | None:
    """The declared form `token` is most plausibly a misspelling of, or None.

    Every step of the key is total, so a tie never falls through to the order
    the forms happened to be compiled in: closest distance first, then highest
    similarity, then best tier, then the form's own spelling.
    """
    best: SurfaceForm | None = None
    best_key: tuple[int, float, int, str] | None = None
    for form in forms:
        budget = _edit_budget(len(form.folded))
        if budget == 0:
            continue
        distance = DamerauLevenshtein.distance(token, form.folded)
        if distance > budget:
            continue
        similarity = JaroWinkler.similarity(token, form.folded)
        if similarity < _MIN_SIMILARITY:
            continue
        key = (distance, -similarity, _TIER_RANK[form.score_tier], form.folded)
        if best_key is None or key < best_key:
            best, best_key = form, key
    return best


def _overlaps(one: tuple[int, int], other: tuple[int, int]) -> bool:
    return one[0] < other[1] and other[0] < one[1]
