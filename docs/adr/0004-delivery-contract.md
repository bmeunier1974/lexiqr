# ADR 0004 — delivery ↔ core/cli/schema contract: PR gates and tag→publish

## Status

Accepted (2026-07-23)

## Context

A solo maintainer means everything runs unattended: CI is the only quality gate, and releases must not depend on long-lived credentials or manual steps. Several capabilities are explicitly CI-enforced guarantees (C9 determinism, C11 performance envelope, C12 quickstart-as-test, C16, C17).

## Decision

- **Protocol:** GitHub Actions triggers — pull request, and `v*` tag push.
- **On PR:** ruff lint, strict mypy, full test suite across Python 3.10–3.13, performance envelope check (`transform()` p95 < 10 ms on a 1,000-surface-form lexicon; init < 1 s), determinism check across the matrix, README quickstart executed as a test.
- **On tag:** build wheel + sdist, publish via **trusted publishing** (OIDC, no long-lived tokens) — to TestPyPI until the pipe is proven end to end, then switched to PyPI; a changelog entry is required per release.
- **Data shapes:** semver tag `vX.Y.Z`; one wheel containing core + cli + bundled schema; a CHANGELOG entry per release.

## Consequences

- The riskiest integration (trusted publishing) is exercised by the walking skeleton (`v0.0.1` → TestPyPI), not discovered at 1.0.
- Perf and determinism regressions fail PRs, making C9/C11 living guarantees rather than README claims.
- The publish flip from TestPyPI to PyPI is a one-line workflow change once proven.
