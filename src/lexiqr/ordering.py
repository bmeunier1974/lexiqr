"""What every ranking in the match pass ends on, so no ordering is partial.

The match pass ranks candidates twice. The fuzzy pass ranks declared surface
forms to pick the one a mistyped word most plausibly names; the overlap resolver
ranks competing hits to pick which one survives the text they both claim. Both
rankings start from things a lexicon author would recognise — how similar, how
long, which tier, where in the sentence — and both eventually run out of them:
two candidates can be alike in every one of those and still be two candidates.

Something must still choose, and choose the same way on every run, machine and
Python version, because determinism (C9) is a tested guarantee rather than an
aspiration. That last component is what this module owns.

It lives apart from the rankings that use it because the claim it makes — *this
is what makes the ordering total* — is one claim, and a claim stated in two sort
keys in two functions is a claim that can come apart. Here it has one home, one
docstring, and one test.
"""

from __future__ import annotations

from typing import Protocol


class Identified(Protocol):
    """A ranked candidate, seen only as the declaration that produced it.

    The two rankings rank different types — a declared surface form on the fuzzy
    side, a hit on it in the resolver — and neither shape is this module's
    business. What both carry is which entry a candidate came from and which
    entity that entry resolves to, so that is all the seam asks for.
    """

    @property
    def canonical_id(self) -> str: ...

    @property
    def entry_id(self) -> str: ...


def identity(candidate: Identified) -> tuple[str, ...]:
    """The final, tie-closing component of a match-pass ordering key.

    **The lower canonical ID wins, then the lower entry ID**, both compared as
    text. That is arbitrary in the way a tiebreak has to be: it is reached only
    once everything a lexicon author would recognise as a reason has already tied,
    and its whole job is to be an answer rather than the *right* answer. What
    matters is that it is always an answer — so no tie ever falls through to the
    order a stage happened to emit its candidates in.

    The entry ID is what keeps it total. The canonical ID alone was total only
    while the entity *was* the key: several entries may now resolve to one entity,
    at which point two candidates can agree on everything above and on the entity,
    and only the entry they were declared under is left to separate them. Entry
    IDs are unique by construction — they are the keys of one object — so the key
    cannot tie twice.

    Read by both `matcher._correction_precedence` and `matcher._precedence`, and
    returned as a tuple so growing what identity means stays one edit here rather
    than two edits in two sort keys that can silently disagree.
    """
    return (candidate.canonical_id, candidate.entry_id)
