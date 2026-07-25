"""The input guard: the one place that decides whether a prompt is acceptable.

These tests drive the guard directly — no resolver, no lexicon, no matching
pipeline — because the guard's whole point is that it answers "is this input
acceptable?" before any of that exists to defend itself. A separate, smaller set
of tests through the public API (below) proves the guard is actually wired in
ahead of matching.
"""

import pytest

from conftest import FLOOFF_LEXICON
from lexiqr import MAX_PROMPT_LENGTH, EntityResolver, ValidationError
from lexiqr.guard import check_prompt, is_blank


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


# --- Empty and whitespace-only input: a defined, ordinary result, not a fault.
# --- These decisions live in the guard alongside the size limit, so the whole
# --- "what does the pipeline accept" policy reads in one place.


@pytest.mark.parametrize(
    "prompt",
    [
        "",  # empty
        "   ",  # spaces
        "\t\n\r",  # tabs and newlines
        "  ",  # non-breaking space, em space (Unicode whitespace)
    ],
)
def test_empty_and_whitespace_only_prompts_are_blank(prompt: str) -> None:
    assert is_blank(prompt) is True


@pytest.mark.parametrize("prompt", ["wo ist flooff", " x ", " a "])
def test_a_prompt_with_any_non_whitespace_is_not_blank(prompt: str) -> None:
    assert is_blank(prompt) is False


# --- Lone surrogates: malformed code points that cannot be encoded to UTF-8.
# --- The guard rejects them at the boundary rather than letting them propagate
# --- into a report that could never be serialized or stored.


@pytest.mark.parametrize(
    "prompt",
    [
        "\ud800",  # lone high surrogate, alone
        "wo ist \ud800 flooff",  # embedded in otherwise-fine text
        "\udfff",  # lone low surrogate
        "flooff\udc00",  # trailing
    ],
)
def test_a_prompt_containing_a_lone_surrogate_is_rejected(prompt: str) -> None:
    with pytest.raises(ValidationError) as caught:
        check_prompt(prompt)

    assert caught.value.field == "prompt"


@pytest.mark.parametrize(
    "prompt",
    [
        "a" + "́" * 500,  # combining-character flood
        "‮wo ist flooff‬",  # bidi override characters
        "wo ist flooff \U0001f600\U0001f389",  # astral-plane emoji
        "wo ist \U00010330 flooff",  # astral-plane rare script
    ],
)
def test_surrogate_free_adversarial_text_is_accepted_unchanged(prompt: str) -> None:
    # The guard bounds and rejects; it never mangles. Anything that is not a
    # lone surrogate or over the size limit passes through untouched, so spans
    # keep indexing the original prompt and normalization policy is unchanged.
    assert check_prompt(prompt) == prompt


# --- The guard, seen through the public API: proof it is wired in ahead of
# --- matching, not merely available as a module.


def test_transform_rejects_an_oversized_prompt_with_the_structured_error() -> None:
    resolver = EntityResolver.from_file(FLOOFF_LEXICON)

    with pytest.raises(ValidationError):
        resolver.transform("x" * (MAX_PROMPT_LENGTH + 1), "de-DE")


def test_the_guard_runs_before_matching_even_when_the_prompt_would_match() -> None:
    # A prompt that contains a real surface form ("flooff") but is padded past
    # the limit must still be rejected: the guard is consulted before any scan,
    # so a hostile prompt costs a rejection rather than a full pipeline pass.
    resolver = EntityResolver.from_file(FLOOFF_LEXICON)
    oversized = "flooff " + "x" * MAX_PROMPT_LENGTH

    with pytest.raises(ValidationError):
        resolver.transform(oversized, "de-DE")


@pytest.mark.parametrize("prompt", ["", "   ", "\t\n", " "])
def test_transform_returns_an_empty_report_for_blank_input(prompt: str) -> None:
    resolver = EntityResolver.from_file(FLOOFF_LEXICON)

    report = resolver.transform(prompt, "de-DE")

    assert report.matches == ()
    assert report.prompt == prompt
    assert report.locale == "de-DE"


def test_whitespace_only_input_is_treated_exactly_like_empty_input() -> None:
    resolver = EntityResolver.from_file(FLOOFF_LEXICON)

    empty = resolver.transform("", "de-DE")
    whitespace = resolver.transform("   ", "de-DE")

    assert empty.matches == whitespace.matches == ()
    assert empty.locale == whitespace.locale


def test_a_prompt_just_under_the_limit_still_resolves_with_valid_spans() -> None:
    resolver = EntityResolver.from_file(FLOOFF_LEXICON)
    padding = "x" * (MAX_PROMPT_LENGTH - len("flooff "))
    prompt = "flooff " + padding
    assert len(prompt) <= MAX_PROMPT_LENGTH

    report = resolver.transform(prompt, "de-DE")

    assert len(report.matches) == 1
    match = report.matches[0]
    assert match.canonical_id == "product"
    assert report.prompt[match.span[0] : match.span[1]] == "flooff"
