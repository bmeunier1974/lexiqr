"""Prompt acceptance: what `transform()` takes, refuses, and answers with nothing.

Three decisions, all asserted here through the public API, because that is the
only place they are observable: acceptance is part of `transform()`, not a stage
a caller can address on its own. A prompt past the documented maximum length is
a *failure* — `ValidationError`, raised ahead of matching, so hostile input
costs a rejection rather than a full pipeline pass. Empty or whitespace-only
input is a *result* — "the user typed nothing" resolves to an empty match
report. A prompt carrying a lone surrogate is malformed at the code-point level
and is refused at the boundary rather than propagating into a report that could
never be serialized.

Everything else is bounded by the size limit and passed on *unchanged*:
acceptance bounds and refuses, it never mangles, which is what keeps every
reported span indexing the prompt the user actually typed.
"""

import pytest

from conftest import FLOOFF_LEXICON
from lexiqr import MAX_PROMPT_LENGTH, EntityResolver, ValidationError


@pytest.fixture
def resolver() -> EntityResolver:
    return EntityResolver.from_file(FLOOFF_LEXICON)


# --- Over the documented maximum length: a failure, decided before matching.


def test_transform_rejects_an_oversized_prompt_with_the_structured_error(
    resolver: EntityResolver,
) -> None:
    with pytest.raises(ValidationError):
        resolver.transform("x" * (MAX_PROMPT_LENGTH + 1), "de-DE")


def test_the_rejection_names_the_prompt_and_reads_as_a_sentence(
    resolver: EntityResolver,
) -> None:
    with pytest.raises(ValidationError) as caught:
        resolver.transform("x" * (MAX_PROMPT_LENGTH + 1), "de-DE")

    error = caught.value
    assert error.field == "prompt"
    assert error.canonical_id is None
    assert error.locale is None
    assert str(MAX_PROMPT_LENGTH) in error.message


def test_the_size_limit_applies_before_matching_even_when_the_prompt_would_match(
    resolver: EntityResolver,
) -> None:
    # A prompt that contains a real surface form ("flooff") but is padded past
    # the limit must still be rejected: acceptance is decided before any scan,
    # so a hostile prompt costs a rejection rather than a full pipeline pass.
    oversized = "flooff " + "x" * MAX_PROMPT_LENGTH

    with pytest.raises(ValidationError):
        resolver.transform(oversized, "de-DE")


def test_a_prompt_at_the_limit_is_accepted_and_echoed_unchanged(
    resolver: EntityResolver,
) -> None:
    prompt = "flooff " + "x" * (MAX_PROMPT_LENGTH - len("flooff "))
    assert len(prompt) == MAX_PROMPT_LENGTH

    report = resolver.transform(prompt, "de-DE")

    assert report.prompt == prompt
    assert len(report.matches) == 1
    match = report.matches[0]
    assert match.canonical_id == "product"
    assert report.prompt[match.span[0] : match.span[1]] == "flooff"


# --- Empty and whitespace-only input: a defined, ordinary result, not a fault.


@pytest.mark.parametrize(
    "prompt",
    [
        "",  # empty
        "   ",  # spaces
        "\t\n",  # tab and newline
        "\t\n\r",  # ... and a carriage return
        " ",  # a single space
        "  ",  # non-breaking space, em space (Unicode whitespace)
    ],
)
def test_transform_returns_an_empty_report_for_blank_input(
    resolver: EntityResolver, prompt: str
) -> None:
    report = resolver.transform(prompt, "de-DE")

    assert report.matches == ()
    assert report.prompt == prompt
    assert report.locale == "de-DE"


def test_whitespace_only_input_is_treated_exactly_like_empty_input(
    resolver: EntityResolver,
) -> None:
    empty = resolver.transform("", "de-DE")
    whitespace = resolver.transform("   ", "de-DE")

    assert empty.matches == whitespace.matches == ()
    assert empty.locale == whitespace.locale


@pytest.mark.parametrize(
    "prompt",
    [
        "wo ist flooff",
        " flooff ",  # padded with ASCII spaces
        " flooff ",  # padded with Unicode whitespace
    ],
)
def test_a_prompt_with_any_non_whitespace_is_resolved_not_short_circuited(
    resolver: EntityResolver, prompt: str
) -> None:
    # The other side of the blank rule: anything holding a non-whitespace
    # character is ordinary input and reaches the pipeline, whatever whitespace
    # — ASCII or Unicode — surrounds it.
    report = resolver.transform(prompt, "de-DE")

    assert [match.canonical_id for match in report.matches] == ["product"]
    match = report.matches[0]
    assert report.prompt[match.span[0] : match.span[1]] == "flooff"


# --- Lone surrogates: malformed code points that cannot be encoded to UTF-8.
# --- They are refused at the boundary rather than left to propagate into a
# --- report that could never be serialized or stored.


@pytest.mark.parametrize(
    "prompt",
    [
        "\ud800",  # lone high surrogate, alone
        "wo ist \ud800 flooff",  # embedded in otherwise-fine text
        "\udfff",  # lone low surrogate
        "flooff\udc00",  # trailing
    ],
)
def test_a_prompt_containing_a_lone_surrogate_is_rejected(
    resolver: EntityResolver, prompt: str
) -> None:
    with pytest.raises(ValidationError) as caught:
        resolver.transform(prompt, "de-DE")

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
def test_surrogate_free_adversarial_text_is_accepted_unchanged(
    resolver: EntityResolver, prompt: str
) -> None:
    # Acceptance bounds and refuses; it never mangles. Anything that is neither
    # a lone surrogate nor over the size limit reaches the pipeline untouched,
    # so spans keep indexing the original prompt and normalization stays the
    # only stage that rewrites anything.
    assert resolver.transform(prompt, "de-DE").prompt == prompt
