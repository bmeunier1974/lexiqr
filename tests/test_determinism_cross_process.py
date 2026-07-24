"""Determinism across separate processes — the layer ordinary tests can't reach.

Within one process, dict and set iteration order is fixed for the run, so a
reordering bug can hide. It shows up across *processes*: Python randomizes string
hashing per interpreter unless `PYTHONHASHSEED` is pinned, so if any ordering in
the pipeline leaned on hash order, a fresh interpreter would resolve the same
prompt differently. This test runs the identical resolution under several hash
seeds in fresh subprocesses and requires byte-identical serialized reports — a
restart, or a colleague's machine, can never change an answer.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from perf.lexicon_generator import generate_benchmark_lexicon, serialize_lexicon

# A resolution driver run in a fresh interpreter: load the lexicon, resolve each
# prompt, and print the canonical serialization of every report, in order.
_CHILD = """
import json, sys
from lexiqr import EntityResolver, serialize_report
path, locale = sys.argv[1], sys.argv[2]
prompts = json.loads(sys.argv[3])
resolver = EntityResolver.from_file(path)
reports = [serialize_report(resolver.transform(p, locale)) for p in prompts]
sys.stdout.write("\\n".join(reports))
"""

_HASH_SEEDS = ["0", "1", "42", "1000003", "random"]


def _prompts_from(lexicon: dict[str, object], locale: str) -> list[str]:
    """Prompts that actually hit the lexicon, so ordering is exercised."""
    words = [
        forms["preferred"]["singular"]
        for entity in lexicon["entities"].values()  # type: ignore[attr-defined]
        for loc, forms in entity["locales"].items()
        if loc == locale
    ]
    picks = words[:12]
    return [
        " ".join(picks[:6]),
        "wo ist " + " und ".join(picks[6:12]),
        " ".join(reversed(picks[:6])) + " xxnoisexx " + " ".join(picks[6:9]),
        "",
    ]


def test_resolution_is_identical_across_hash_seeds(tmp_path: Path) -> None:
    lexicon = generate_benchmark_lexicon(target_surface_forms=300)
    locale = "de-DE"
    path = tmp_path / "bench.lexicon.json"
    path.write_text(serialize_lexicon(lexicon), encoding="utf-8")
    prompts = _prompts_from(lexicon, locale)

    outputs: list[str] = []
    for seed in _HASH_SEEDS:
        env = {"PYTHONHASHSEED": seed} if seed != "random" else {}
        result = subprocess.run(
            [sys.executable, "-c", _CHILD, str(path), locale, json.dumps(prompts)],
            capture_output=True,
            text=True,
            check=True,
            env={**_base_env(), **env},
        )
        outputs.append(result.stdout)

    assert len(set(outputs)) == 1, "resolution diverged across hash seeds"
    # And the reports were not all empty — the prompts genuinely matched.
    assert any('"canonical_id"' in line for line in outputs[0].splitlines())


def _base_env() -> dict[str, str]:
    import os

    # Preserve the environment (PATH, virtualenv) but let each run set its own
    # PYTHONHASHSEED; dropping it entirely would randomize the seed per run.
    env = dict(os.environ)
    env.pop("PYTHONHASHSEED", None)
    return env


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
