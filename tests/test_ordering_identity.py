"""The identity component both match-pass rankings end on has one home.

Determinism (C9) rests on each ordering in the match pass being *total*: no tie
may fall through to whichever candidate a stage happened to emit first. Two
rankings make that claim — the fuzzy pass choosing the form a typo most
plausibly names, and the overlap resolver choosing which competing hit survives —
and both close on the same idea: when nothing about the text separates two
candidates, identity decides.

These tests hold the two sites to one answer. They are not about *which* way the
tiebreak falls, which is arbitrary by construction; they are about the two sites
being unable to drift into different ideas of what breaks a tie.
"""

import pytest

from lexiqr.index import Hit, SurfaceForm
from lexiqr.matcher import _Claim, _correction_precedence, _precedence
from lexiqr.ordering import identity
from lexiqr.types import ScoreTier


def _form(canonical_id: str, folded: str = "cafe") -> SurfaceForm:
    return SurfaceForm(
        folded=folded,
        canonical_id=canonical_id,
        surface_form=folded,
        score_tier=ScoreTier.PREFERRED,
    )


def _hit(canonical_id: str, folded: str = "cafe") -> Hit:
    return Hit(
        canonical_id=canonical_id,
        surface_form=folded,
        span=(0, len(folded)),
        score_tier=ScoreTier.PREFERRED,
    )


def test_a_hit_and_the_declared_form_it_came_from_have_one_identity() -> None:
    """The two rankings rank different types — a declared form and a hit on it.

    If the seam read a different field from each, the two sites would break the
    same tie differently while both looking like they consulted one rule.
    """
    assert identity(_form("bistro")) == identity(_hit("bistro"))


@pytest.mark.parametrize(("one", "other"), [("bistro", "diner"), ("diner", "bistro")])
def test_both_rankings_break_a_tie_the_way_the_seam_does(one: str, other: str) -> None:
    """Two candidates alike in everything the rankings ask about but identity.

    Whichever way the seam orders them, both sites must order them that way. The
    pair is passed in both orders so a site that inverted the seam, or ignored it
    for a rule of its own, cannot pass by accident.
    """
    expected = identity(_form(one)) < identity(_form(other))

    correction_ranking = _correction_precedence(
        similarity=1.0, distance=0, form=_form(one)
    ) < _correction_precedence(similarity=1.0, distance=0, form=_form(other))
    overlap_ranking = _precedence(_Claim(_hit(one), is_fuzzy=False)) < _precedence(
        _Claim(_hit(other), is_fuzzy=False)
    )

    assert correction_ranking is expected
    assert overlap_ranking is expected
