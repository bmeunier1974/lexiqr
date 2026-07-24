"""The performance benchmark behind the CI perf gate (C11).

The vision states an envelope: `transform()` p95 under 10 ms against a
1,000-surface-form lexicon, and initialization under 1 second. This module turns
that envelope into something measurable, and something CI can fail a PR on.

The measurement method is part of the contract, so it is fixed and stated:

- **Initialization is measured cold** — one `EntityResolver` built from the
  generated lexicon, timed once, with nothing warmed.
- **`transform()` p95 excludes warm-up** — a fixed number of warm-up calls run
  first and are discarded, then p95 is taken over a fixed number of timed
  iterations against the same lexicon.
- The lexicon is the seeded 1,000-surface-form fixture (story #52), so the
  number means something for a realistic tenant and is identical every run.

The gate asserts the envelope **multiplied by a headroom factor**, not the
envelope itself. Shared CI runners are noisy; the headroom turns that noise into
a re-run rather than a false red. It is stated here, next to the envelope, so
nobody mistakes the gate threshold for the guarantee: a change has to make
matching roughly an order of magnitude slower to trip this gate, and catching
subtle drift is deliberately not its job — the non-gating recorded timings are
where a trend would show.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

try:  # importable as `perf.benchmark` under pytest (tests/ is on the path)
    from perf.lexicon_generator import count_surface_forms, generate_benchmark_lexicon
except ModuleNotFoundError:  # run standalone: `python tests/perf/benchmark.py`
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from perf.lexicon_generator import count_surface_forms, generate_benchmark_lexicon

from lexiqr import EntityResolver

#: The vision's envelope — the guarantee, stated in the README.
ENVELOPE_TRANSFORM_P95_MS = 10.0
ENVELOPE_INITIALIZATION_S = 1.0

#: The stated headroom the gate multiplies the envelope by, so runner noise
#: produces a re-run rather than a false failure. Not the guarantee — the gate.
HEADROOM = 3.0

#: Fixed measurement parameters (part of the contract): warm-up is discarded,
#: p95 is taken over this many timed iterations.
WARMUP_ITERATIONS = 100
TRANSFORM_ITERATIONS = 1500
LONG_PROMPT_ITERATIONS = 300

_LOCALE = "de-DE"


def _locale_singulars(lexicon: dict[str, Any]) -> list[str]:
    """Every preferred singular declared in the benchmark locale, sorted.

    Sorted so the prompts below are deterministic rather than dependent on dict
    order, and drawn from the lexicon so they actually resolve.
    """
    return sorted(
        forms["preferred"]["singular"]
        for entity in lexicon["entities"].values()
        for locale, forms in entity["locales"].items()
        if locale == _LOCALE
    )


def representative_prompt(lexicon: dict[str, Any]) -> str:
    """A realistic request-path query: a handful of real surface forms."""
    return "wo ist " + " ".join(_locale_singulars(lexicon)[:6])


def long_prompt(lexicon: dict[str, Any]) -> str:
    """A long-but-under-limit prompt — much longer than a query, still realistic.

    Real surface forms interleaved with ordinary non-matching words, because
    that mix is what a real long prompt looks like: the non-matching words are
    the ones the fuzzy pass actually works on, so this exercises the cost the
    envelope has to cover, not just cheap exact hits. It proves the size limit
    is the only cliff — performance degrades gradually with length rather than
    falling off before the guard's ceiling.
    """
    real = _locale_singulars(lexicon)[:50]
    noise = [f"beispielwort{index:03d}" for index in range(50)]
    interleaved = [word for pair in zip(real, noise, strict=True) for word in pair]
    return " ".join(interleaved)


def measure_initialization_seconds(lexicon: dict[str, Any]) -> float:
    """Cold initialization: build one resolver, timed, nothing warmed."""
    start = time.perf_counter()
    EntityResolver.from_dict(lexicon)
    return time.perf_counter() - start


def measure_transform_p95_ms(
    resolver: EntityResolver,
    prompt: str,
    *,
    iterations: int = TRANSFORM_ITERATIONS,
    warmup: int = WARMUP_ITERATIONS,
) -> float:
    """p95 latency of `transform()` in milliseconds, warm-up excluded."""
    for _ in range(warmup):
        resolver.transform(prompt, _LOCALE)
    samples = []
    for _ in range(iterations):
        start = time.perf_counter()
        resolver.transform(prompt, _LOCALE)
        samples.append((time.perf_counter() - start) * 1000)
    samples.sort()
    return samples[min(len(samples) - 1, int(0.95 * len(samples)))]


def run() -> dict[str, float]:
    """Measure the whole envelope once and return the raw numbers."""
    lexicon = generate_benchmark_lexicon()
    resolver = EntityResolver.from_dict(lexicon)
    return {
        "surface_forms": float(count_surface_forms(lexicon)),
        "initialization_s": measure_initialization_seconds(lexicon),
        "transform_p95_ms": measure_transform_p95_ms(
            resolver, representative_prompt(lexicon)
        ),
        "long_prompt_p95_ms": measure_transform_p95_ms(
            resolver, long_prompt(lexicon), iterations=LONG_PROMPT_ITERATIONS
        ),
    }


def gate_failures(measurements: dict[str, float]) -> list[str]:
    """The envelope×headroom checks that failed, if any — empty means passing."""
    p95_ceiling = ENVELOPE_TRANSFORM_P95_MS * HEADROOM
    init_ceiling = ENVELOPE_INITIALIZATION_S * HEADROOM
    failures = []
    if measurements["initialization_s"] > init_ceiling:
        failures.append(
            f"initialization {measurements['initialization_s']:.3f}s exceeds "
            f"{init_ceiling:.1f}s (envelope {ENVELOPE_INITIALIZATION_S}s × {HEADROOM})"
        )
    if measurements["transform_p95_ms"] > p95_ceiling:
        failures.append(
            f"transform p95 {measurements['transform_p95_ms']:.3f}ms exceeds "
            f"{p95_ceiling:.1f}ms (envelope {ENVELOPE_TRANSFORM_P95_MS}ms × {HEADROOM})"
        )
    if measurements["long_prompt_p95_ms"] > p95_ceiling:
        failures.append(
            f"long-prompt p95 {measurements['long_prompt_p95_ms']:.3f}ms exceeds "
            f"{p95_ceiling:.1f}ms (envelope {ENVELOPE_TRANSFORM_P95_MS}ms × {HEADROOM})"
        )
    return failures


def _format(measurements: dict[str, float]) -> str:
    return (
        f"surface_forms={int(measurements['surface_forms'])} "
        f"init={measurements['initialization_s'] * 1000:.1f}ms "
        f"transform_p95={measurements['transform_p95_ms']:.3f}ms "
        f"long_prompt_p95={measurements['long_prompt_p95_ms']:.3f}ms"
    )


def main(argv: list[str]) -> int:
    measurements = run()
    # Always record the raw timings, so a trend is visible even on a pass.
    print(_format(measurements))

    if "--check" not in argv:
        return 0

    failures = gate_failures(measurements)
    if failures:
        print("PERF GATE FAILED:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print(
        f"perf gate OK: envelope × {HEADROOM} headroom met "
        f"(p95 < {ENVELOPE_TRANSFORM_P95_MS * HEADROOM:.0f}ms, "
        f"init < {ENVELOPE_INITIALIZATION_S * HEADROOM:.0f}s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
