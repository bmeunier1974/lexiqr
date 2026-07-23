# Foundations — lexicon model, validation, quality gates

## Capabilities covered

- C2 — An integrating developer can initialize a lexicon instance from structured multilingual lexicon data (JSON file or Python dict) conforming to lexiqr's versioned entity schema: each entity has a canonical ID plus per-locale surface forms (preferred singular/plural, alternate labels).
- C3 — An integrating developer supplying invalid lexicon data gets precise, human-readable validation errors identifying the offending entity, locale, and field.
- C10 — An integrating developer gets full type hints (`py.typed`): IDE completion works and the package passes strict type-checking as a dependency.
- C13 — A lexicon author can validate their lexicon file against a published, versioned JSON Schema using standard tooling, without installing anything from lexiqr.
- C16 — A maintainer sees every pull request automatically run lint (ruff), strict type-check (mypy), and the test suite across Python 3.10–3.13.

## Problem

The skeleton has a toy lexicon shape and no guardrails. Every later plan builds on the lexicon data model and lands behind the quality gate, so both must be complete and strict *now* — retrofitting typing or validation is far more expensive than starting with them.

## Solution

Finalize lexicon schema v1 (full shape: `schemaVersion`, default locale, entities, per-locale preferred singular/plural + alternates), implement core's load-time validation with structured errors (entity/locale/field), and test the ADR 0003 equivalence guarantee (schema-pass ⇒ core-load, with beyond-schema semantic checks documented). Ship `py.typed` with a strict-mypy-clean public API. Extend CI to the full PR gate: ruff, strict mypy, tests on 3.10–3.13.

## Scope

- Full lexicon v1 schema + published tagged URL; fixture corpus (valid and invalid lexicons).
- `EntityResolver` init from JSON file or dict; structured `ValidationError` per ADR 0002.
- Equivalence test harness (standard JSON Schema validator vs core load).
- `py.typed`, strict mypy config, ruff config; CI matrix 3.10–3.13 on every PR.

## Out of scope

- Any matching behavior changes; `lexiqr validate` CLI (plan 006); perf/determinism gates (plan 007).

## Dependencies

001 — walking skeleton.
