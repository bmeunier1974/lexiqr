# Release 1.0 — quickstart, PyPI, semver

## Capabilities covered

- C1 — An integrating developer can install the package from PyPI into a clean Python ≥3.10 environment with `pip install lexiqr`.
- C12 — An integrating developer can follow the README quickstart to reproduce the founding scenario — a German tenant's lexicon mapping "flooff" (and the typo "floof") to the `product` entity — in under 5 minutes.
- C17 — A maintainer can cut a release by pushing a version tag: CI builds the distribution and publishes it to PyPI via trusted publishing (no long-lived tokens), with semver and a changelog entry per release.

## Problem

The skeleton proved the publish pipe against TestPyPI; v1.0 must land on real PyPI from a public repo with a copy-paste quickstart, a semver/changelog discipline, and the legal heritage question settled.

## Solution

Flip trusted publishing to real PyPI (ADR 0004's one-line change) with the `lexiqr` name registered. Write the README quickstart around the flooff scenario — including the "floof" typo correction — and execute it verbatim as a CI test. Establish semver + CHANGELOG-entry-required release flow. Gate the public release on the heritage constraint: confirm branch-735 release rights, or document the port as a clean-room reimplementation of the design. Cut v1.0.0 by tag.

## Scope

- PyPI project + trusted-publisher config; publish workflow flip from TestPyPI.
- README quickstart (flooff + floof), extracted and run as a CI test; clean-venv install test from PyPI.
- CHANGELOG + release checklist; changelog-entry CI check on tags.
- **Release-rights gate:** written confirmation for branch-735 heritage, or a clean-room note in the repo.
- Multi-tenant recipe doc (tenant→instance mapping as a documented recipe, per the vision non-goal).

## Out of scope

- CONTRIBUTING.md, issue/PR templates, fork CI (explicitly post-1.0); marketing/announcement.

## Dependencies

All prior plans (001–007) — 1.0 ships the complete capability set.
