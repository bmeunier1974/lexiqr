# Hardening — bounded input, determinism, performance envelope

## Capabilities covered

- C8 — An integrating developer calling `transform()` with empty, oversized, or adversarial Unicode input gets a bounded-time response with a clear result or error — never a hang or crash.
- C9 — An integrating developer running the same lexicon, prompt, and configuration gets an identical result across runs and platforms — determinism is a tested guarantee.
- C11 — An integrating developer can rely on a stated, CI-enforced performance envelope: `transform()` p95 under 10 ms against a 1,000-surface-form lexicon; initialization under 1 second.

## Problem

lexiqr's pitch *is* "deterministic and production-ready": those words are only true if adversarial input, cross-platform nondeterminism, and performance regressions are tested guarantees enforced by CI — not README claims.

## Solution

Port the branch-735 security, property-based, and perf test suites (the preserved behavioral spec). Input hardening: documented size limits with clear errors, bounded-time handling of adversarial Unicode (combining-character floods, bidi controls, astral-plane text), empty-input as a defined result. Determinism: property-based tests plus byte-identical match-report comparison across the CI matrix (all Python versions and platforms). Performance: a benchmark against a generated 1,000-surface-form lexicon asserting the envelope (p95 < 10 ms transform, < 1 s init) as a CI gate with headroom against runner noise.

## Scope

- Input bounds + adversarial Unicode handling in normalize/scan/fuzzy paths.
- Property-based determinism suite (hypothesis) and cross-platform report-equality CI job.
- Perf benchmark fixture + CI gate; envelope documented in README.
- Port of branch-735 security + property + perf tests.

## Out of scope

- Performance work beyond meeting the envelope; async APIs; sandboxing.

## Dependencies

003, 004, 005 — the full matching pipeline must exist to be hardened.
