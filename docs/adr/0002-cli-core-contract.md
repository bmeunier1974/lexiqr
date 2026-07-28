# ADR 0002 — cli ↔ core contract: public API only, in-process

## Status

Accepted (2026-07-23). The `MatchReport` shape it names is extended by
[ADR 0005](0005-entry-metadata-format.md): a match also carries the entry that
answered and that entry's metadata. The contract itself — public API only,
in-process, one validation code path — stands unchanged.

## Context

The CLI (`lexiqr validate`, `lexiqr try`) serves lexicon authors who never write Python, yet capability C14 requires the CLI to emit *the same* precise validation errors the library raises at load time. Duplicating validation or formatting logic in the CLI would let the two drift.

## Decision

- **Protocol:** in-process Python calls, restricted to core's **public** API surface — the exact API integrating developers use. The CLI imports nothing from private modules.
- **Operations:** load-and-validate a lexicon (raising structured validation errors), construct an `EntityResolver`, call `transform(prompt, locale)`.
- **Data shapes:**
  - `Lexicon` input — dict/JSON conforming to lexicon schema v1.
  - `ValidationError` — structured, carrying the offending entity ID, locale, and field (C3); the CLI renders it, never rewrites it.
  - `MatchReport` — original prompt, resolved locale, ordered list of `EntityMatch` (canonical ID, matched surface form, character span, score tier, applied correction, matched locale).

## Consequences

- C14's error parity holds **by construction**: there is one validation code path.
- The CLI doubles as a living test of the public API's ergonomics — if the CLI needs a private import, the public API is missing something.
- Core's structured errors and report types are public API and therefore semver-governed.
