"""Canonical serialization of a `MatchReport` — public, semver-governed API.

Determinism is only useful to an integrating developer if they can *hold* it:
turn a resolution result into a stable form, snapshot it in their own test suite,
diff two snapshots, store one and compare it to another months later. That is
what this module is for. lexiqr's own determinism tests consume exactly this
surface, so the guarantee is verified through the API developers use rather than
a private back door.

The form is **canonical**, not merely deterministic. Two byte-equal
serializations mean two equal reports and nothing else:

- Object keys are emitted in a fixed (sorted) order, so field order never varies.
- The match list keeps the report's own order — the pipeline decides ranking,
  and the serialization records it faithfully rather than re-sorting it.
- Output is pure ASCII with no insignificant whitespace, so it carries no
  environment-dependent value (locale, platform, interpreter) that could make
  two equal reports serialize differently.

The form **round-trips**: `deserialize_report(serialize_report(r)) == r`, and
re-serializing yields the identical string. Round-tripping restores the *types*,
not just the values: a filter read back out of storage is the same immutable
mapping a fresh resolution hands over, so a stored report still compares equal to
the one it was stored from.

The shape is semver-governed **from the first release tag onward**: once
published, it can only change on a major version. Before that tag it is still
being settled — the entry ID and the filter were added to every match here, which
broke any snapshot taken from an earlier build, and doing it then rather than
after publication is the whole reason the promise is worded this way.
"""

from __future__ import annotations

import json
from typing import Any

from lexiqr.metadata import Metadata, MetadataValue
from lexiqr.types import EntityMatch, MatchReport, ScoreTier


def serialize_report(report: MatchReport) -> str:
    """Return the canonical string form of `report`.

    Byte-identical for equal reports, on every platform and interpreter.
    """
    payload = {
        "prompt": report.prompt,
        "locale": report.locale,
        "matches": [_match_to_payload(match) for match in report.matches],
    }
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    )


def deserialize_report(text: str) -> MatchReport:
    """Reconstruct the `MatchReport` a canonical string was serialized from."""
    payload = json.loads(text)
    return MatchReport(
        prompt=payload["prompt"],
        locale=payload["locale"],
        matches=tuple(_match_from_payload(match) for match in payload["matches"]),
    )


def _match_to_payload(match: EntityMatch) -> dict[str, Any]:
    """Every field of the match, unconditionally.

    `entry_id` is always a string and `metadata` always an object — empty when the
    entry declared no filter. Emitting them only when the feature was used would
    make a consumer branch on whether a key exists, and would make two reports of
    the same lexicon differ in shape rather than in content.
    """
    return {
        "canonical_id": match.canonical_id,
        "entry_id": match.entry_id,
        "surface_form": match.surface_form,
        "span": [match.span[0], match.span[1]],
        "score_tier": match.score_tier.value,
        "matched_locale": match.matched_locale,
        "correction": match.correction,
        "metadata": _metadata_to_payload(match.metadata),
    }


def _match_from_payload(payload: dict[str, Any]) -> EntityMatch:
    start, end = payload["span"]
    return EntityMatch(
        canonical_id=payload["canonical_id"],
        entry_id=payload["entry_id"],
        surface_form=payload["surface_form"],
        span=(start, end),
        score_tier=ScoreTier(payload["score_tier"]),
        matched_locale=payload["matched_locale"],
        correction=payload["correction"],
        metadata=_metadata_from_payload(payload["metadata"]),
    )


def _metadata_to_payload(metadata: Metadata) -> dict[str, Any]:
    """A filter as JSON: a set of scalars becomes an array, everything else is
    itself. Keys need no sorting here — a `Metadata` is already in sorted order,
    and `sort_keys` on the dump settles it either way."""
    return {
        key: list(value) if isinstance(value, tuple) else value
        for key, value in metadata.items()
    }


def _metadata_from_payload(payload: dict[str, Any]) -> Metadata:
    """The inverse, back to the immutable type — so a report read from storage
    carries the same guarantee as one just produced, and compares equal to it."""
    restored: dict[str, MetadataValue] = {
        key: tuple(value) if isinstance(value, list) else value
        for key, value in payload.items()
    }
    return Metadata(restored)
