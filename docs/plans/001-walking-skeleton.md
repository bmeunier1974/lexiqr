# Walking skeleton — "flooff" resolves end to end

## Capabilities covered

- C18 — An OSS contributor can clone the public GitHub repo, set up the dev environment with one command (`uv sync`), and run the full test suite locally.
- Thin slices (completed in later plans): C2, C4, C13, C15, C16, C17.

## Problem

Nothing exists yet. The riskiest integrations — package layout, wheel build, trusted publishing, schema/core equivalence — must be proven before feature work piles on top of unvalidated plumbing.

## Solution

The thinnest deployed path touching all four containers, exactly as defined in [BLUEPRINT.md](../../BLUEPRINT.md):

1. **schema** — `schema/lexicon.v1.schema.json` with the minimal shape; a one-entity fixture lexicon (`product` ← "flooff", locale `de-DE`) validates against it with a standard validator.
2. **core** — `EntityResolver(lexicon)` loads the fixture; `transform("wo ist flooff", "de-DE")` returns one exact match: entity `product`, surface "flooff", correct character span. Exact match only — no fuzzy, no fallback, no accent handling.
3. **cli** — `lexiqr try lexicon.json --locale de-DE "wo ist flooff"` prints that match report.
4. **delivery** — `uv sync` bootstraps the dev env; CI runs the above as tests on one Python version; tag `v0.0.1` builds the wheel and publishes to **TestPyPI** via trusted publishing; a clean venv installs from TestPyPI and reproduces the match.

## Scope

- `src/lexiqr/` package skeleton with `EntityResolver` and a minimal typed match report.
- Minimal schema v1 file with `$id` on the raw-GitHub tagged-URL convention (ADR 0003).
- `lexiqr try` console entry point (argparse), happy path only.
- `pyproject.toml` (hatchling, rapidfuzz dependency), single-version CI workflow, tag→TestPyPI publish workflow.

## Out of scope

- Validation errors, fuzzy matching, locale fallback, accents, `lexiqr validate`, the CI matrix, real PyPI — all later plans.

## Dependencies

None.
