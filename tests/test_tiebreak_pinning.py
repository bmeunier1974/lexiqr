"""Underdetermined orderings pinned to explicit, documented tie-breakers.

Determinism (C9) requires every ordering in the pipeline to be *total* — no tie
may fall through to whichever hit a stage happened to emit first. Most were
pinned by earlier epics; these are the residual same-fold cases property-based
testing forces into the open, where two surface forms fold to the same text and
claim the identical span at the identical tier. Each has an explicit rule, and
each is locked here as a deliberate behavior decision, verified stable rather
than left to iteration order.
"""

from conftest import lexicon_document
from lexiqr import EntityResolver


def test_two_forms_of_one_entity_that_fold_alike_resolve_by_declaration_order() -> None:
    # "café" and "cafe" are both alternates of one entity and both fold to
    # "cafe": same span, same tier, same entity. The index keeps the
    # first-declared, so the first alternate wins — deterministically, on every
    # run and machine — rather than a second candidate reaching the resolver.
    document = lexicon_document(
        "de-DE",
        product={
            "preferred": {"singular": "widget"},
            "alternates": ["café", "cafe"],
        },
    )
    resolver = EntityResolver.from_dict(document)

    report = resolver.transform("ich mag café heute", "de-DE")

    assert len(report.matches) == 1
    assert report.matches[0].surface_form == "café"  # first-declared alternate


def test_two_entities_whose_forms_fold_alike_resolve_by_lower_canonical_id() -> None:
    # Two *different* entities declaring forms that fold to the same text ("cafe"
    # and "café" → "cafe") is not the cross-entity ambiguity the loader rejects
    # (their casefolds differ), so both reach the overlap resolver claiming the
    # same span at the same tier. Rule 4 breaks it on the lower canonical ID:
    # "bistro" < "diner", every time.
    document = lexicon_document(
        "de-DE",
        diner={"preferred": {"singular": "café"}},
        bistro={"preferred": {"singular": "cafe"}},
    )
    resolver = EntityResolver.from_dict(document)

    report = resolver.transform("das café dort", "de-DE")

    assert len(report.matches) == 1
    assert report.matches[0].canonical_id == "bistro"
