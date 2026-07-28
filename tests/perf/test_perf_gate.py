"""The performance gate (C11), as a test selected only by the perf job.

Marked `perf`, so the default test run deselects it — measuring latency in the
ordinary Python matrix would be noisy and pointless. The dedicated single-runner
CI job selects it with `-m perf`; a contributor can too. It asserts the vision's
envelope × the stated headroom, so it goes red only on a large regression, which
is exactly the trade the headroom buys. Raw timings are recorded separately, un-
gated, for trend-watching.
"""

import pytest

from lexiqr import MAX_PROMPT_LENGTH, EntityResolver
from perf import benchmark
from perf.lexicon_generator import generate_benchmark_lexicon

pytestmark = pytest.mark.perf


@pytest.fixture(scope="module")
def measurements() -> dict[str, float]:
    """Measure the whole envelope once for every assertion below."""
    return benchmark.run()


def test_the_benchmark_lexicon_is_the_thousand_form_fixture(
    measurements: dict[str, float],
) -> None:
    assert measurements["surface_forms"] >= 1000


def test_initialization_is_within_the_envelope_with_headroom(
    measurements: dict[str, float],
) -> None:
    ceiling = benchmark.ENVELOPE_INITIALIZATION_S * benchmark.HEADROOM
    assert measurements["initialization_s"] <= ceiling


def test_transform_p95_is_within_the_envelope_with_headroom(
    measurements: dict[str, float],
) -> None:
    ceiling = benchmark.ENVELOPE_TRANSFORM_P95_MS * benchmark.HEADROOM
    assert measurements["transform_p95_ms"] <= ceiling


def test_a_long_but_under_limit_prompt_still_meets_the_envelope(
    measurements: dict[str, float],
) -> None:
    # The prompt is genuinely long yet under the guard's ceiling, so the size
    # limit — not a hidden performance cliff — is the only edge.
    lexicon = generate_benchmark_lexicon()
    assert len(benchmark.long_prompt(lexicon)) <= MAX_PROMPT_LENGTH

    ceiling = benchmark.ENVELOPE_TRANSFORM_P95_MS * benchmark.HEADROOM
    assert measurements["long_prompt_p95_ms"] <= ceiling


def test_the_gate_summary_reports_no_failures(
    measurements: dict[str, float],
) -> None:
    assert benchmark.gate_failures(measurements) == []


def test_the_envelope_holds_for_a_lexicon_whose_every_entry_carries_a_filter(
    measurements: dict[str, float],
) -> None:
    """Adopting filters must cost nothing per request.

    The fixture every assertion above measures declares metadata on every entry
    (`tests/perf/test_lexicon_generator.py` guards that), so the envelope those
    assertions check is already the with-filters envelope. This says so where the
    envelope is stated, and fails if the fixture ever stops using the feature.
    """
    lexicon = generate_benchmark_lexicon()

    assert all(entity.get("metadata") for entity in lexicon["entities"].values())
    assert measurements["transform_p95_ms"] <= (
        benchmark.ENVELOPE_TRANSFORM_P95_MS * benchmark.HEADROOM
    )


def test_a_filter_is_carried_by_reference_rather_than_copied_per_match() -> None:
    """The mechanism the envelope above rests on.

    A filter is immutable, so every match on an entry can point at the one object
    the loader built. Copying per hit would make the cost scale with matches rather
    than with entries, and the envelope would erode quietly as tenants adopt the
    feature — so the sharing is pinned rather than assumed.
    """
    lexicon = generate_benchmark_lexicon()
    resolver = EntityResolver.from_dict(lexicon)
    words = sorted(
        forms["preferred"]["singular"]
        for entity in lexicon["entities"].values()
        for locale, forms in entity["locales"].items()
        if locale == "de-DE"
    )

    twice = resolver.transform(f"{words[0]} und {words[0]}", "de-DE")

    assert len(twice.matches) == 2
    assert twice.matches[0].metadata is twice.matches[1].metadata
