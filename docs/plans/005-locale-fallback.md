# Locale fallback chains

## Capabilities covered

- C6 — An integrating developer can configure a locale fallback chain at initialization (default: exact locale → same-language variants → lexicon's declared default), and the match report states which locale actually matched.

## Problem

Tenants rarely author every surface form in every locale variant. A `de-AT` prompt against a lexicon authored in `de-DE` should still resolve — predictably, with the report saying which locale actually matched, never by silent guessing.

## Solution

A fallback chain resolved at initialization: default policy exact locale → same-language variants → the lexicon's declared default locale, overridable by an explicit chain passed to `EntityResolver`. The scan walks the chain deterministically; each match carries the locale that actually matched (`matched-locale` field from ADR 0002). Locale tags are treated as opaque BCP 47 — no language detection (vision non-goal).

## Scope

- Chain construction (default policy + explicit override) validated at init.
- Chain-aware scan with deterministic precedence (earlier chain entries always win).
- `matched_locale` populated in `EntityMatch`; resolved locale in `MatchReport`.
- Tests for variant fallback, default-locale fallback, and override chains.

## Out of scope

- Language detection; per-call chain overrides; merging matches across locales beyond chain precedence.

## Dependencies

003 — exact matching & normalization. (Independent of 004.)
