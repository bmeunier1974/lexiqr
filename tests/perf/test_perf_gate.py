"""The performance gate (C11), as a test selected only by the perf job.

Marked `perf`, so the default test run deselects it — measuring latency in the
ordinary Python matrix would be noisy and pointless. The dedicated single-runner
CI job selects it with `-m perf`; a contributor can too. It asserts the vision's
envelope × the stated headroom, so it goes red only on a large regression, which
is exactly the trade the headroom buys. Raw timings are recorded separately, un-
gated, for trend-watching.
"""

import pytest

from lexiqr.guard import MAX_PROMPT_LENGTH
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
