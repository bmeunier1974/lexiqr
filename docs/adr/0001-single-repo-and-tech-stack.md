# ADR 0001 — Single repo for all four containers; Python + rapidfuzz + uv stack

## Status

Accepted (2026-07-23)

## Context

[BLUEPRINT.md](../../BLUEPRINT.md) decomposes lexiqr into four C4 containers: core, cli, schema, delivery. The standard pipeline scaffolds one repo per container plus a meta-repo. lexiqr, however, is a single pip-installable library: core and cli ship in one wheel, schema is bundled with (and versioned alongside) the format core implements, and delivery is the repo's own CI. The maintainer is solo.

## Decision

One repository serves as both meta-repo and product repo. Containers keep hard boundaries as paths, not repos:

- **core** → `src/lexiqr/` (excluding `cli.py`)
- **cli** → `src/lexiqr/cli.py`
- **schema** → `schema/`
- **delivery** → `.github/workflows/` + `pyproject.toml`

Tech stack, per container (from BLUEPRINT.md):

- **core**: Python ≥3.10; rapidfuzz as the *sole* runtime dependency (prebuilt wheels everywhere); `py.typed`. Ports the proven branch-735 pipeline (normalize → lexicon scan → fuzzy pass → match report); the branch-735 test suite is the behavioral spec.
- **cli**: stdlib argparse only; console entry point in the same wheel.
- **schema**: JSON Schema draft 2020-12; `$id` = raw.githubusercontent.com URL of a tagged path (immutable, zero infra).
- **delivery**: GitHub Actions + uv + hatchling; TestPyPI via trusted publishing until the pipe is proven, then PyPI.

## Consequences

- One `git init`, one CI setup, one issue tracker; no cross-repo version skew is possible.
- Container boundaries are enforced by review and tests (e.g. cli imports only from core's public API), not by repo walls — the contract ADRs (0002–0004) are the reference.
- `docs/plans/` holds the plans of *all* containers, prefixed by container name where ambiguous; Plan 001 (walking skeleton) spans all four by design.
- If a container ever needs its own cadence (e.g. schema evolving independently post-1.0), it can be extracted; the path boundaries make that a mechanical move.
