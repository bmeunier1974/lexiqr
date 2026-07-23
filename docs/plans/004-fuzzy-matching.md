# Typo-tolerant (fuzzy) matching

## Capabilities covered

- C5 — An integrating developer observes typo-tolerant matching: a misspelled surface form (e.g. "floof" for "flooff") still resolves, within length-aware edit budgets, and the match report shows the applied correction; fuzzy matching can be disabled via configuration.

## Problem

Users mistype jargon ("floof" for "flooff"); exact matching alone silently drops those, and the alternatives (LLM guessing, per-tenant embedding retraining) are exactly what lexiqr exists to replace. Tolerance must stay deterministic and explainable.

## Solution

Port the branch-735 fuzzy pass (behavioral spec: the preserved fuzzy test suite) on top of the exact scan: rapidfuzz-backed candidate matching within length-aware edit budgets (short forms tolerate less), deterministic tie-breaking, and an explicit `correction` record in the match (what was typed → which surface form it was corrected to). Exact matches always outrank fuzzy ones. A configuration flag at `EntityResolver` init disables the fuzzy pass entirely.

## Scope

- Fuzzy pass with length-aware edit budgets and deterministic candidate ranking.
- `correction` populated in `EntityMatch`; spans still aligned to the original text.
- `fuzzy=False` (or equivalent) configuration; documented budget table.
- Port of branch-735 fuzzy tests; the "floof" → "flooff" case as a named test.

## Out of scope

- Phonetic or semantic similarity; per-tenant tuning knobs beyond on/off; perf gating (007).

## Dependencies

003 — exact matching & normalization.
