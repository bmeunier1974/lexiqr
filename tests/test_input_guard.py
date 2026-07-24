"""The input guard: the one place that decides whether a prompt is acceptable.

These tests drive the guard directly — no resolver, no lexicon, no matching
pipeline — because the guard's whole point is that it answers "is this input
acceptable?" before any of that exists to defend itself. A separate, smaller set
of tests through the public API (below) proves the guard is actually wired in
ahead of matching.
"""

from pathlib import Path

import pytest

from lexiqr import EntityResolver, ValidationError
from lexiqr.guard import MAX_PROMPT_LENGTH, check_prompt

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "examples" / "flooff.lexicon.json"
)


def test_a_prompt_over_the_maximum_length_is_rejected() -> None:
    with pytest.raises(ValidationError):
        check_prompt("x" * (MAX_PROMPT_LENGTH + 1))


def test_the_rejection_names_the_prompt_and_reads_as_a_sentence() -> None:
    with pytest.raises(ValidationError) as caught:
        check_prompt("x" * (MAX_PROMPT_LENGTH + 1))

    error = caught.value
    assert error.field == "prompt"
    assert error.canonical_id is None
    assert error.locale is None
    assert str(MAX_PROMPT_LENGTH) in error.message


def test_a_prompt_at_the_limit_is_accepted_and_returned_unchanged() -> None:
    prompt = "x" * MAX_PROMPT_LENGTH

    assert check_prompt(prompt) == prompt


def test_an_ordinary_prompt_passes_through_the_guard_untouched() -> None:
    assert check_prompt("wo ist flooff") == "wo ist flooff"


# --- The guard, seen through the public API: proof it is wired in ahead of
# --- matching, not merely available as a module.


def test_transform_rejects_an_oversized_prompt_with_the_structured_error() -> None:
    resolver = EntityResolver.from_file(FIXTURE_PATH)

    with pytest.raises(ValidationError):
        resolver.transform("x" * (MAX_PROMPT_LENGTH + 1), "de-DE")


def test_the_guard_runs_before_matching_even_when_the_prompt_would_match() -> None:
    # A prompt that contains a real surface form ("flooff") but is padded past
    # the limit must still be rejected: the guard is consulted before any scan,
    # so a hostile prompt costs a rejection rather than a full pipeline pass.
    resolver = EntityResolver.from_file(FIXTURE_PATH)
    oversized = "flooff " + "x" * MAX_PROMPT_LENGTH

    with pytest.raises(ValidationError):
        resolver.transform(oversized, "de-DE")


def test_a_prompt_just_under_the_limit_still_resolves_with_valid_spans() -> None:
    resolver = EntityResolver.from_file(FIXTURE_PATH)
    padding = "x" * (MAX_PROMPT_LENGTH - len("flooff "))
    prompt = "flooff " + padding
    assert len(prompt) <= MAX_PROMPT_LENGTH

    report = resolver.transform(prompt, "de-DE")

    assert len(report.matches) == 1
    match = report.matches[0]
    assert match.canonical_id == "product"
    assert report.prompt[match.span[0] : match.span[1]] == "flooff"
