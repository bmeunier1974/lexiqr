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

## [1.0.0] - 2026-08-04

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
- **Several terms may resolve to one entity, each with a discriminating filter**
  (ADR 0005). What a lexicon's `entities` object keys is an **entry**: a named
  set of surface forms plus the entity it resolves to. An entry may declare
  `canonicalId`, which **defaults to the entry ID** when omitted, and several
  entries may name the same one — "movie" and "series" can both be `product`
  without inventing entities the backend does not have. Every match names the
  entry that answered (`entry_id`) alongside the entity your backend queries
  (`canonical_id`).
- **An entry may carry `metadata`**: a tenant-defined bag, at most 16 keys, each
  value a string, a number, a boolean, or a list of unique strings. No `null`, no
  nesting. lexiqr **carries it and never interprets it** — every match reports its
  entry's metadata verbatim, and metadata never influences which matches are
  returned, their score tiers, or their order. `Metadata` and `MetadataValue` are
  public and fully hinted, so a consuming service builds a search filter straight
  from a match report with no per-tenant table of its own.
- **`Lexicon` and `SurfaceForms` are public.** `Lexicon` is the declared
  parameter type of `EntityResolver(...)`, and validation is construction — so
  `Lexicon.from_file` / `Lexicon.from_dict` give an integrating developer a
  validation-only workflow (load a tenant's file, catch `ValidationError`) with
  no throwaway resolver, and a resolver can be built from a lexicon the caller
  already holds. `SurfaceForms` is the per-entity, per-locale shape a lexicon
  holds, and `Entry` is what `Lexicon.entries` yields — each entry's ID, the
  entity it resolves to, and its filter.
- **Structured errors.** `ValidationError` carries the coordinates (canonical
  id, locale, field) that make a rejected lexicon actionable without debugging
  lexiqr. `MalformedDocumentError` names the load failure that has no
  coordinates — the file is not JSON, so it never became a document and nothing
  in it can be pointed at. It subclasses `ValidationError`, so code catching the
  general load failure catches it too; catching it by name tells "that file is
  not a lexicon document" from "that lexicon says the wrong thing".
- **Validation matches the published schema exactly.** Entry keys and
  `canonicalId` values are checked against the schema's identifier pattern
  (letters, digits, `_`, `.`, `-`), so both sides of the ADR 0003 equivalence
  contract give the same verdict. Beyond the schema, the semantic checks in
  [docs/lexicon-semantic-checks.md](docs/lexicon-semantic-checks.md) include:
  a `canonicalId` may not point at an entry that itself resolves elsewhere (a
  target is an entity, not another entry), and a metadata value may not be only
  whitespace — it would become a live filter that silently narrows every query.
- **Canonical report serialization** — `serialize_report` / `deserialize_report`
  produce a byte-stable form that round-trips and only changes on a major
  release, so a stored snapshot stays comparable. `entry_id` and `metadata` are
  always emitted — metadata an object, empty when the entry declares none — so
  a consumer's parser never branches on whether a key is present.
- **Bounded, guarded input** — a fixed prompt limit enforced before matching,
  and adversarial Unicode handled in bounded time. Both documented limits are
  public constants — `MAX_PROMPT_LENGTH` (10,000 characters) and
  `MAX_SURFACE_FORM_LENGTH` (128 characters) — so callers sizing input or
  generating labels read the number lexiqr enforces instead of copying it.
- **`lexiqr` CLI** for lexicon authors — `validate` and `try` — with a
  scriptable exit-code contract. Both commands load through `Lexicon.from_file`
  like any other caller, so the message an author reads is core's own sentence,
  under the CLI's prefix — one wording, one code path (ADR 0002). `try` shows
  which entry answered and what filter it carried — two lines, printed only
  when they say something.
- **Typed and self-contained** — ships `py.typed` and the versioned JSON Schema
  inside a pure-Python wheel, with rapidfuzz as the sole runtime dependency.
  Package metadata follows PEP 639: the license is an SPDX expression
  (`License-Expression: MIT`, Metadata-Version 2.4) with the LICENSE file
  shipped in the wheel's `dist-info/licenses/`.
- **Stated, CI-enforced performance envelope** — `transform()` p95 < 10 ms and
  cold initialization < 1 s against the seeded 1,000-surface-form benchmark.
- **Executable README quickstart** — the founding flooff story for both the
  developer and the lexicon author, run in CI against the README's own inline
  lexicon so the front page cannot drift from the shipped API.
- **A full sample run demonstrates the whole contract in one command** —
  `uv run python examples/demo.py` resolves a realistic tenant lexicon
  (`examples/medien.lexicon.json`) and prints twelve narrated sections, each
  stating a claim, showing what lexiqr produced, and asserting it; a false
  claim exits non-zero naming the section that broke. Its full output is a
  committed golden the test suite compares against, the README documents the
  command with a verified excerpt, and the release workflow runs it against the
  freshly published wheel — so a publish is verified by twelve claims, not one.
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
