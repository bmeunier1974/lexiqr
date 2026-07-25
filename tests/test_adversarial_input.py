"""Adversarial Unicode through the public API — the load-bearing behaviour of C8.

`transform()` must answer hostile free-form text with a clear result or a
structured error, never a hang, a crash, or a corrupted match. These tests
exercise that guarantee through the public API, with `fuzzy` on and off, so it
is never quietly conditional on configuration. They assert external behaviour
only: what `transform()` returns or raises, whether it stays within a generous
time ceiling, and that every returned span still indexes the original prompt.
"""

import time

import pytest

from lexiqr import EntityResolver, MatchReport, ValidationError

FIXTURE = "examples/flooff.lexicon.json"

#: A ceiling generous enough that only a genuine hang trips it — this is a
#: liveness check, not a performance measurement. Adversarial inputs here
#: resolve in single-digit milliseconds; seconds would mean something is wrong.
_HANG_CEILING_SECONDS = 2.0


@pytest.fixture(params=[True, False], ids=["fuzzy-on", "fuzzy-off"])
def resolver(request: pytest.FixtureRequest) -> EntityResolver:
    """Both configurations — the guarantee must hold identically for each."""
    return EntityResolver.from_file(FIXTURE, fuzzy=request.param)


def spans_are_valid(report: MatchReport) -> bool:
    """Every match span slices the original prompt without raising or drifting."""
    return all(
        0 <= start <= end <= len(report.prompt) and report.prompt[start:end] != ""
        for start, end in (match.span for match in report.matches)
    )


def test_a_combining_character_flood_is_handled_in_bounded_time(
    resolver: EntityResolver,
) -> None:
    flood = "a" + "́" * 9_000  # a base letter drowned in combining accents

    started = time.perf_counter()
    report = resolver.transform(flood, "de-DE")
    elapsed = time.perf_counter() - started

    assert elapsed < _HANG_CEILING_SECONDS
    assert isinstance(report, MatchReport)
    assert spans_are_valid(report)


def test_a_combining_flood_around_a_real_word_stays_bounded_and_valid(
    resolver: EntityResolver,
) -> None:
    prompt = "wo ist flooff" + "́" * 5_000

    started = time.perf_counter()
    report = resolver.transform(prompt, "de-DE")
    elapsed = time.perf_counter() - started

    assert elapsed < _HANG_CEILING_SECONDS
    assert spans_are_valid(report)


def test_bidi_controls_do_not_distort_what_resolves(resolver: EntityResolver) -> None:
    # A right-to-left override around the prompt is a display trick, not a change
    # to the logical code-point order matching works on — so "flooff" still
    # resolves, at a span that still slices to "flooff" in the original text.
    prompt = "‮wo ist flooff‬"

    report = resolver.transform(prompt, "de-DE")

    assert spans_are_valid(report)
    assert [m.canonical_id for m in report.matches] == ["product"]
    match = report.matches[0]
    assert report.prompt[match.span[0] : match.span[1]] == "flooff"


def test_astral_plane_text_is_handled_without_crashing(
    resolver: EntityResolver,
) -> None:
    for prompt in (
        "wo ist flooff \U0001f600\U0001f389",  # emoji
        "wo ist \U00010330 flooff",  # Gothic, an astral-plane script
    ):
        report = resolver.transform(prompt, "de-DE")

        assert spans_are_valid(report)
        assert [m.canonical_id for m in report.matches] == ["product"]


@pytest.mark.parametrize(
    "prompt",
    ["\ud800", "wo ist \ud800 flooff", "flooff\udc00"],
)
def test_a_lone_surrogate_is_rejected_through_the_public_api(
    resolver: EntityResolver, prompt: str
) -> None:
    with pytest.raises(ValidationError):
        resolver.transform(prompt, "de-DE")
