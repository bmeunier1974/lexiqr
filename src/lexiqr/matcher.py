"""The match pass: a prompt and one locale's surface forms → entity matches.

Three stages behind one interface. The exact scan claims every occurrence of
every declared surface form it can find. The fuzzy pass then looks only at the
words no exact hit touched, and asks whether any of them is a near-miss of a
declared form. One overlap resolver decides between everything the two produced,
by one total rule, and orders the survivors. A caller sees none of that: `scan`
takes a prompt and a prebuilt index and returns the ordered matches.

Both stages work in normalized text, because that is the only text their
patterns were folded to fit. A caller works in the prompt they typed. Every
hit — exact or fuzzy — crosses that line exactly once, at the bottom of this
module, and a fuzzy hit picks up its correction in the same crossing: the
original words its span points at.

That an exact hit beats a fuzzy one is enforced twice, on purpose. The fuzzy
pass never examines text an exact hit covered, which is what keeps tolerance
from costing anything on a prompt the scan already resolved; and the resolver
asks kind before it asks anything about the text, which is what makes the
guarantee hold rather than merely usually happen. Cost and correctness are two
reasons, so they stay two mechanisms — adjacent here, where the second is
readable as the backstop for the first.

Scoring is rapidfuzz, already the library's only runtime dependency: a
Damerau-Levenshtein distance, so a transposition costs one edit the way people
actually mistype, and a Jaro-Winkler similarity to rank near-misses of equal
distance. This module is the only place in core that reasons about edit distance
and similarity, so a tolerance regression points here and nowhere else.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz.distance import DamerauLevenshtein, JaroWinkler

from lexiqr.index import WORD_CHARACTER, Hit, SurfaceForm, SurfaceFormIndex
from lexiqr.normalizer import Normalized, normalize
from lexiqr.ordering import identity
from lexiqr.types import EntityMatch, ScoreTier

#: Best tier first. The enum orders by declaration, but that is a fact about the
#: enum; the ranking matching depends on is stated here — once, for both the
#: correction ranking and the overlap resolver, which cannot disagree about
#: which tier is better because there is only one answer to read.
_TIER_RANK = {
    ScoreTier.PREFERRED: 0,
    ScoreTier.ALTERNATE: 1,
    ScoreTier.CANONICAL: 2,
}

#: A ranking key: mixed components, uniformly comparable, read left to right.
#: Both rankings splice `ordering.identity` into theirs, and how wide that is
#: belongs to that module, so neither key can be spelled as a fixed-length tuple.
_Key = tuple[float | str, ...]

#: A residue token is a run of the index's word characters: the same rule the
#: exact scan applies when it requires a form to stand alone, stated there and
#: read here, so the two passes cannot drift into different ideas of where a
#: word ends.
_WORD = re.compile(rf"{WORD_CHARACTER.pattern}+")


@dataclass(frozen=True)
class _Claim:
    """One hit competing for text, and which pass produced it.

    The hit is the index's `Hit`, whichever pass found it: both kinds carry the
    same fields with the same meanings, in the same normalized coordinates, so
    neither is copied into a second shape on its way here. Kind is what is left,
    and it is not a property of the hit but of how it was found — it decides an
    overlap, and it decides whether the match carries a correction.
    """

    hit: Hit
    is_fuzzy: bool


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
    near_misses = _fuzzy_pass(normalized, covered, index) if fuzzy_enabled else ()

    claims = tuple(_Claim(hit, is_fuzzy=False) for hit in exact) + tuple(
        _Claim(hit, is_fuzzy=True) for hit in near_misses
    )
    return tuple(
        _to_match(claim, normalized, prompt, locale) for claim in _resolve(claims)
    )


#: Tolerance scales with how much evidence a surface form carries. A three-letter
#: jargon term gets no edits — otherwise it collides with every other short word
#: in the prompt and no one can explain why "cat" resolved to `product`. Four to
#: five characters earn a single edit, six or more earn two. The boundaries are
#: published in docs/matching-rules.md.
_LONG_FORM = 6
_MEDIUM_FORM = 4

#: On top of the distance budget: a candidate must also be this similar, so the
#: library never reaches for a wildly different word just because the distance
#: happened to fit. Below it, nothing matches.
_MIN_SIMILARITY = 0.90


def _fuzzy_pass(
    normalized: Normalized,
    covered: tuple[tuple[int, int], ...],
    index: SurfaceFormIndex,
) -> tuple[Hit, ...]:
    """Near-miss hits over the words the exact scan left uncovered.

    Exact matching claims what it can and stops. Whatever surface form a user
    misspelled it never sees, because a typo is by definition not the string the
    automaton was built from. This pass picks up from there and nowhere else:
    the text no exact hit `covered` is the only text it reads, which is both why
    tolerance never rewrites a match the caller could already trust and why it
    costs nothing on a prompt the scan already resolved.

    Single words are matched against single-word forms; adjacent word pairs are
    matched against multi-word forms, in the order typed and swapped, so phrase
    jargon tolerates a misspelled word or two words in the wrong order. Both
    kinds are emitted; the overlap resolver keeps the longest where a pair and
    one of its words both matched.
    """
    forms = _fuzzy_candidates(index.forms())
    single_forms = tuple(form for form in forms if " " not in form.folded)
    multi_forms = tuple(form for form in forms if " " in form.folded)

    tokens = _tokens(normalized.text)
    hits: list[Hit] = []
    for token, span in tokens:
        if _overlaps_any(span, covered):
            continue
        best = _best_candidate(token, single_forms)
        if best is not None:
            hits.append(_hit(best, span))
    for (left, left_span), (right, right_span) in zip(tokens, tokens[1:], strict=False):
        if _overlaps_any(left_span, covered) or _overlaps_any(right_span, covered):
            continue
        span = (left_span[0], right_span[1])
        best = _best_candidate(f"{left} {right}", multi_forms) or _best_candidate(
            f"{right} {left}", multi_forms
        )
        if best is not None:
            hits.append(_hit(best, span))
    return tuple(hits)


def _edit_budget(folded_length: int) -> int:
    """The edit budget a surface form of this folded length earns."""
    if folded_length >= _LONG_FORM:
        return 2
    if folded_length >= _MEDIUM_FORM:
        return 1
    return 0


def _hit(form: SurfaceForm, span: tuple[int, int]) -> Hit:
    """A near-miss, reported in the shape and coordinates an exact hit uses."""
    return Hit(
        canonical_id=form.canonical_id,
        surface_form=form.surface_form,
        span=span,
        score_tier=form.score_tier,
    )


def _fuzzy_candidates(forms: tuple[SurfaceForm, ...]) -> tuple[SurfaceForm, ...]:
    """The declared vocabulary a typo may be tolerated against.

    The canonical ID rides along in the index as a surface form of last resort,
    so a prompt that names it outright still resolves. But it is the identifier
    the tenant never sees, and tolerating *misspellings* of it would let a user
    word drift into an internal name it never meant — so fuzzy matching reaches
    only for the tenant's own preferred and alternate labels.
    """
    return tuple(form for form in forms if form.score_tier is not ScoreTier.CANONICAL)


def _tokens(text: str) -> list[tuple[str, tuple[int, int]]]:
    """Every word token of `text`, with its span, in order."""
    return [
        (match.group(), (match.start(), match.end())) for match in _WORD.finditer(text)
    ]


def _overlaps_any(span: tuple[int, int], covered: tuple[tuple[int, int], ...]) -> bool:
    """Whether `span` touches any region the exact scan already claimed."""
    return any(_overlaps(span, region) for region in covered)


def _best_candidate(token: str, forms: tuple[SurfaceForm, ...]) -> SurfaceForm | None:
    """The declared form `token` is most plausibly a misspelling of, or None.

    The ranking is `_correction_precedence`, and it is totally ordered, so the
    same typo resolves to the same form on every run, machine, and Python version
    — determinism (C9) holds for fuzzy results as it does for exact ones. The
    documented earliest-start rule orders the emitted matches and belongs to the
    overlap resolver below, where positions actually differ.
    """
    best: SurfaceForm | None = None
    best_key: _Key | None = None
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
        key = _correction_precedence(
            similarity=similarity, distance=distance, form=form
        )
        if best_key is None or key < best_key:
            best, best_key = form, key
    return best


def _correction_precedence(
    *, similarity: float, distance: int, form: SurfaceForm
) -> _Key:
    """Sort key putting the form a typo most plausibly names first.

    1. **Higher similarity wins**, then **lower edit distance**, then the
       **better tier**: how close the guess is, before whose vocabulary it is.
    2. **Then `ordering.identity` decides** — the shared component that makes this
       ordering total, so two candidates alike in every reason above still resolve
       the same way on every machine.
    3. **Then the form's own spelling**, which separates two forms of one entity
       that are equally plausible readings of the same typo. It sits after
       identity rather than before it because identity is the coarser fact, and
       swapping them would change which form an ambiguous typo resolves to.
    """
    return (
        -similarity,
        distance,
        _TIER_RANK[form.score_tier],
        *identity(form),
        form.folded,
    )


def _resolve(claims: tuple[_Claim, ...]) -> tuple[_Claim, ...]:
    """Drop the hits that lose an overlap, and order the rest by position.

    The scan is deliberately greedy: it reports "support ticket" and the
    "ticket" inside it, because it cannot know which one the tenant meant, and
    the fuzzy pass adds near-misses on top. Something has to decide between all
    of them, and the decision is observable — a caller who snapshot-tests a
    report depends on it — so it is made by one total rule rather than by
    whichever hit a stage happened to emit first. That rule is `_precedence`.
    """
    kept: list[_Claim] = []
    for claim in sorted(claims, key=_precedence):
        if not any(_overlaps(claim.hit.span, chosen.hit.span) for chosen in kept):
            kept.append(claim)
    return tuple(sorted(kept, key=lambda claim: claim.hit.span))


def _precedence(claim: _Claim) -> _Key:
    """Sort key putting the hit that should win an overlap first.

    0. **An exact hit beats an overlapping fuzzy one**, whatever their spans. A
       word the user spelled correctly is never displaced by a guess about a word
       they didn't. Kind is asked before anything about the text — and it is
       asked even though the fuzzy pass already skipped every covered word,
       because a guarantee that rests on a cost optimization is not a guarantee.
    1. **The longest span wins.** A tenant who wrote a precise multi-word label
       meant that label, not the shorter ones it happens to contain.
    2. **Then the better tier wins.** Their own vocabulary beats a synonym, and a
       synonym beats the identifier they never see.
    3. **Then the earlier start wins.**
    4. **Then `ordering.identity` decides.** Two *different* entities can declare
       surface forms that fold to the same text — "cafe" and "café" both fold to
       "cafe" — and claim the same span at the same tier, which leaves nothing
       about the text to choose between them. Which of them is picked, and why
       that answer is arbitrary, is the seam's to state; that something is always
       picked is what makes this ordering total.

    Rules 0–3 encode what a lexicon author meant, so they live here. (Two forms of
    the *same* entity that fold alike never reach here: the index keeps the
    first-declared one, so only one hit is ever emitted for them.)
    """
    start, end = claim.hit.span
    return (
        claim.is_fuzzy,
        start - end,
        _TIER_RANK[claim.hit.score_tier],
        start,
        *identity(claim.hit),
    )


def _overlaps(one: tuple[int, int], other: tuple[int, int]) -> bool:
    """Whether two spans claim any of the same text.

    The only overlap rule in matching: the residue filter and the resolver ask
    the same question of the same coordinates, and get the same answer.
    """
    return one[0] < other[1] and other[0] < one[1]


def _to_match(
    claim: _Claim, normalized: Normalized, prompt: str, locale: str
) -> EntityMatch:
    """Translate a surviving claim back to the prompt the caller typed.

    A fuzzy claim carries a correction — the original words its span points at,
    so a highlighted span still marks what the user actually typed. An exact one
    carries none.
    """
    start, end = normalized.to_original_span(*claim.hit.span)
    return EntityMatch(
        canonical_id=claim.hit.canonical_id,
        surface_form=claim.hit.surface_form,
        span=(start, end),
        score_tier=claim.hit.score_tier,
        matched_locale=locale,
        correction=prompt[start:end] if claim.is_fuzzy else None,
    )
