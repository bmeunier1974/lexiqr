# ADR 0003 — core ↔ schema contract: shared document format, equivalence guarantee

## Status

Accepted (2026-07-23)

## Context

Lexicon authors validate their files against a published JSON Schema using standard tooling, without installing lexiqr (C13). Core independently validates the same documents at load time with precise, human-readable errors (C3). Two validators over one format can drift.

## Decision

- **Protocol:** shared document format — the lexicon JSON. There is no runtime coupling: core never fetches the schema; the schema executes no code.
- **Versioning:** lexicon files declare their format version in a `schemaVersion` field; core pins the schema version(s) it implements and rejects others with a clear error.
- **Equivalence guarantee:** a file that passes the published JSON Schema **must** load in core. Core may enforce *stricter semantic* checks the schema cannot express (e.g. duplicate surface forms across entities); every beyond-schema check is documented as such.
- **Data shapes:** a lexicon document = schema version, default locale, entities keyed by canonical ID, per-locale surface forms (preferred singular/plural, alternate labels).

## Consequences

- The equivalence guarantee is testable: CI validates fixture lexicons with a standard JSON Schema validator *and* loads them with core, asserting agreement (schema-pass ⇒ core-load).
- Schema changes are format changes: a new `schemaVersion`, a new schema file at a new tagged URL, and a core release that pins it.
- Authors get editor tooling and offline validation for free; core stays the sole authority on semantics.
