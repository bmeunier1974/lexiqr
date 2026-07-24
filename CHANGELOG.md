# Changelog

All notable changes to lexiqr are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
lexiqr adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html):
the release tag is `vMAJOR.MINOR.PATCH`, optionally with a prerelease suffix
(`v1.0.0-rc.1`). **Every release carries its own entry here** — written by hand,
non-empty, and matching the tag. The release-consistency gate
(`scripts/release_consistency.py`) enforces this on every tag push: a tag whose
version disagrees with this file, or that has no entry here, fails before the
package is built. See that module's docstring for the full rule.

Pending changes accumulate under **Unreleased**; cutting a release moves them
down under a new `## [x.y.z]` heading dated on the day it ships.

## [Unreleased]

_Nothing yet._

## [1.0.0] - 2026-07-24

The initial public release of lexiqr: deterministic, tenant-scoped resolution of
company jargon to canonical entities, on PyPI.

### Added

- **Deterministic resolution engine.** `EntityResolver` transforms free-form
  prompts into entity-identified match reports — exact and typo-tolerant matches
  with character spans, score tiers, and corrections — reproducibly within and
  across processes and platforms.
- **Typo tolerance** on by default (`fuzzy=True`); every fuzzy match carries a
  correction naming what was typed. `fuzzy=False` gives exact-only behaviour.
- **Multilingual, locale-aware lexicons** with locale fallback, so a prompt read
  in one locale can resolve through its declared fallbacks.
- **Structured errors.** `ValidationError` carries the coordinates (canonical
  id, locale, field) that make a rejected lexicon actionable without debugging
  lexiqr.
- **Canonical report serialization** — `serialize_report` / `deserialize_report`
  produce a byte-stable form that round-trips and only changes on a major
  release, so a stored snapshot stays comparable.
- **Bounded, guarded input** — a fixed 10,000-character prompt limit enforced
  before matching, and adversarial Unicode handled in bounded time.
- **`lexiqr` CLI** for lexicon authors — `validate` and `try` — with a
  scriptable exit-code contract.
- **Typed and self-contained** — ships `py.typed` and the versioned JSON Schema
  inside a pure-Python wheel, with rapidfuzz as the sole runtime dependency.
- **Stated, CI-enforced performance envelope** — `transform()` p95 < 10 ms and
  cold initialization < 1 s against the seeded 1,000-surface-form benchmark.
- **Executable README quickstart** — the founding flooff story for both the
  developer and the lexicon author, run in CI against the README's own inline
  lexicon so the front page cannot drift from the shipped API.
- **Semver-governed surface named explicitly** — the public API, the structured
  error types, the match report types, and the canonical serialization.

### Release infrastructure

- Trusted-publishing release workflow to real PyPI (OIDC, no long-lived token),
  gated by a release-consistency check — the tag, the package version, and the
  top changelog entry must agree — that runs before build, with a post-publish
  job that installs from PyPI into a clean virtualenv and reproduces the flooff
  match (C1).
- `CHANGELOG.md` (Keep a Changelog), the `HERITAGE.md` clean-room provenance note
  beside the MIT `LICENSE`, and the `RELEASING.md` checklist.
