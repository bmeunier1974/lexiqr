"""Determinism when several entries resolve to one entity.

Every ordering in the match pass ends on identity, and identity used to be the
canonical ID alone. That was total only because no two candidates could share
one: the entity was the key. The entry model breaks that — "movie" and "series"
are two entries with one canonical ID — so two candidates can now tie on every
component of the key and fall through to whichever the scan happened to emit
first. This is the regression suite for that hole: it was written before the
identity seam grew and failed then.

The tie is reached with forms that *fold* alike in two different entries — "café"
and "cafe" both fold to "cafe" — which is the one way two candidates can claim the
identical span at the identical tier. The cross-entity ambiguity check does not
refuse them, because their casefolds differ.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any

from conftest import lexicon_document
from lexiqr import EntityResolver, serialize_report

#: Two entries resolving to `product`, whose forms fold to the same text. `alpha`
#: is declared *second* on purpose: if anything still leaned on declaration order,
#: `zebra` would win and the assertions below would say so.
SHARED_ENTITY_DOCUMENT: dict[str, Any] = lexicon_document(
    "de-DE",
    zebra={
        "canonicalId": "product",
        "locales": {"de-DE": {"preferred": {"singular": "café"}}},
    },
    alpha={
        "canonicalId": "product",
        "locales": {"de-DE": {"preferred": {"singular": "cafe"}}},
    },
)

PROMPT = "das café dort"

_CHILD = """
import json, sys
from lexiqr import EntityResolver, serialize_report
document, prompt, locale = json.loads(sys.argv[1]), sys.argv[2], sys.argv[3]
report = EntityResolver.from_dict(document).transform(prompt, locale)
sys.stdout.write(serialize_report(report))
"""

_HASH_SEEDS = ["0", "1", "42", "1000003", "random"]


def test_a_complete_tie_between_two_entries_of_one_entity_is_broken_by_identity() -> (
    None
):
    """Same entity, same span, same tier, same fold: nothing else is left.

    The lower entry ID wins — arbitrary, as a tiebreak must be, and the same on
    every machine. Declaration order would also be *an* answer, but it is not a
    total one: it depends on which stage emitted a candidate first, and that is
    exactly what determinism cannot rest on.
    """
    resolver = EntityResolver.from_dict(SHARED_ENTITY_DOCUMENT)

    report = resolver.transform(PROMPT, "de-DE")

    assert [(m.canonical_id, m.surface_form) for m in report.matches] == [
        ("product", "cafe")
    ]


def test_repeated_resolutions_serialize_to_the_same_bytes() -> None:
    """Asserted through the serialization an integrating developer snapshots with,
    not through a private view of how the match was found."""
    resolver = EntityResolver.from_dict(SHARED_ENTITY_DOCUMENT)

    serialized = {
        serialize_report(resolver.transform(PROMPT, "de-DE")) for _ in range(8)
    }

    assert len(serialized) == 1


def test_the_tie_resolves_the_same_way_in_a_fresh_process() -> None:
    """Within one process, dict order is fixed for the run, so a tie broken by
    iteration order can hide. It shows up under a different hash seed."""
    outputs = set()
    for seed in _HASH_SEEDS:
        env = dict(os.environ)
        env.pop("PYTHONHASHSEED", None)
        if seed != "random":
            env["PYTHONHASHSEED"] = seed
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                _CHILD,
                json.dumps(SHARED_ENTITY_DOCUMENT),
                PROMPT,
                "de-DE",
            ],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        outputs.add(result.stdout)

    assert len(outputs) == 1, outputs
    assert '"canonical_id":"product"' in outputs.pop()
