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
re-serializing yields the identical string. It is semver-governed from the
moment it ships — its shape can only change on a major version.
"""

from __future__ import annotations

import json
from typing import Any

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
    return {
        "canonical_id": match.canonical_id,
        "surface_form": match.surface_form,
        "span": [match.span[0], match.span[1]],
        "score_tier": match.score_tier.value,
        "matched_locale": match.matched_locale,
        "correction": match.correction,
    }


def _match_from_payload(payload: dict[str, Any]) -> EntityMatch:
    start, end = payload["span"]
    return EntityMatch(
        canonical_id=payload["canonical_id"],
        surface_form=payload["surface_form"],
        span=(start, end),
        score_tier=ScoreTier(payload["score_tier"]),
        matched_locale=payload["matched_locale"],
        correction=payload["correction"],
    )
