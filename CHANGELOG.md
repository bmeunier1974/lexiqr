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

Pending for **1.1.0** — the version `pyproject.toml` already declares. Cutting
the release moves these notes into a `## [1.1.0]` heading dated on the day it
ships; until then the top released entry below stays 1.0.0.

### Added

- **`Lexicon` and `SurfaceForms` are public.** `Lexicon` is the declared
  parameter type of `EntityResolver(...)`, and validation is construction — so
  `Lexicon.from_file` / `Lexicon.from_dict` now give an integrating developer a
  validation-only workflow (load a tenant's file, catch `ValidationError`) with
  no throwaway resolver, and a resolver can be built from a lexicon the caller
  already holds. `SurfaceForms` is the per-entity, per-locale shape a lexicon
  holds.
- **The two documented limits are public constants** — `MAX_PROMPT_LENGTH`
  (10,000 characters) and `MAX_SURFACE_FORM_LENGTH` (128 characters) — so
  callers sizing input or generating labels read the number lexiqr enforces
  instead of copying it. Both were already documented and fixed; only their
  visibility changed.

- **`MalformedDocumentError` names the load failure that has no coordinates** —
  the file is not JSON, so it never became a document and nothing in it can be
  pointed at. It subclasses `ValidationError`, so code catching the general load
  failure is unaffected; catching it by name tells "that file is not a lexicon
  document" from "that lexicon says the wrong thing". `lexiqr validate` and
  `lexiqr try` now load through `Lexicon.from_file` like any other caller
  instead of reading and parsing the file themselves, so the malformed-JSON
  message an author reads is core's own sentence, under the CLI's prefix — one
  wording, one code path (ADR 0002). CLI output and exit codes are unchanged.

- **Several terms may resolve to one entity, each with a discriminating filter**
  (ADR 0005). What a lexicon's `entities` object keys is now read as an **entry**:
  a named set of surface forms plus the entity it resolves to. An entry may
  declare `canonicalId`, which **defaults to the entry ID** when omitted — so
  every lexicon written before this means exactly what it always meant — and
  several entries may name the same one. "movie" and "series" can both be
  `product` without inventing entities the backend does not have.
- **An entry may carry `metadata`**: a tenant-defined bag, at most 16 keys, each
  value a string, a number, a boolean, or a list of unique strings. No `null`, no
  nesting. lexiqr **carries it and never interprets it** — every match reports its
  entry's metadata verbatim, and metadata never influences which matches are
  returned, their score tiers, or their order. `Metadata` and `MetadataValue` are
  public and fully hinted, so a consuming service builds a search filter straight
  from a match report with no per-tenant table of its own.
- **`Entry` is public**, so a caller walking `Lexicon.entries` can name what it
  finds and read each entry's ID, the entity it resolves to, and its filter.
- **`lexiqr try` shows which entry answered and what filter it carried** — two
  lines, printed only when they say something, so a lexicon using neither feature
  renders exactly as before. Exit codes and `lexiqr validate` output are unchanged.
- **Two new beyond-schema checks**, both in
  [docs/lexicon-semantic-checks.md](docs/lexicon-semantic-checks.md): a
  `canonicalId` may not point at an entry that itself resolves elsewhere (a target
  is an entity, not another entry), and a metadata value may not be only
  whitespace — it would become a live filter that silently narrows every query.

### Changed

- **The published JSON Schema is amended in place** and republished at the pending
  tag: `$id`, `schema/published.json`, every `$schema` reference and the authoring
  guide's URL all moved together. The previous tag keeps resolving to the bytes it
  had. `RELEASING.md` now documents the republication procedure and names the test
  that enforces it. There is deliberately **no second schema version** — justified
  by the pre-publication window and nothing else (ADR 0005).

### Breaking

Nothing has been published to PyPI, so none of these can affect an installed
consumer; all three were free before the first release tag and impossible after
it, which is why they land now.

- **`EntityMatch` gained two fields and reordered.** `entry_id` is always a real
  string — equal to the canonical ID for an entry that resolves to itself, rather
  than an optional meaning "same as the canonical ID" — which puts it positionally
  ahead of `correction`. `metadata` is last, defaulting to the empty mapping. Code
  constructing an `EntityMatch` positionally must be updated; code reading fields
  by name is unaffected, and `canonical_id` still means the entity your backend
  queries.
- **`serialize_report` always emits `entry_id` and `metadata`.** Metadata is an
  object, empty when the entry declares none — no conditional emission, so a
  consumer's parser never branches on whether a key is present. Any snapshot taken
  from an earlier build must be regenerated. Round-tripping restores the types, so
  a stored report still compares equal to the one it was stored from, and the
  module's shape promise now says it binds from the first release tag onward.
- **Identifier validation tightened.** Core accepted any string as an entity key,
  which was looser than the published schema. Both the entry key and the
  `canonicalId` value are now checked against the schema's pattern (letters,
  digits, `_`, `.`, `-`), so both sides of the ADR 0003 equivalence contract give
  the same verdict. A lexicon that already passed the published schema is
  unaffected.

Otherwise additive: resolution behaviour is unchanged for a lexicon that does not
use the new fields, and nothing else became public — the fallback, index, locale,
matcher, normalizer and ordering machinery stays internal.

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
- `CHANGELOG.md` (Keep a Changelog), the MIT `LICENSE`, and the `RELEASING.md`
  checklist.
