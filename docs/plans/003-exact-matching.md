# Exact matching & normalization

## Capabilities covered

- C4 — An integrating developer can call `transform(prompt, locale)` and receive a typed match report: the original prompt, the resolved locale, and an ordered list of entity matches, each with canonical entity ID, matched surface form, character span in the original text, and score tier (preferred > alternate > canonical).
- C7 — An integrating developer sees accent-insensitive matching for Latin-script locales (diacritics stripped, spans still aligned to the original text) and script-preserving matching for Arabic.

## Problem

The skeleton matches one literal surface form. Real prompts need the full deterministic pipeline: normalization that survives accents without losing character positions, a lexicon scan across all surface forms, and a complete, ordered, span-accurate match report.

## Solution

Port the branch-735 normalize → lexicon scan → match report pipeline (behavioral spec: `.claude/plan/735-python-prompt-transformer-recon.md`, which documents the design; the suites it describes are not preserved in this repo). Normalization casefolds and strips diacritics for Latin-script locales while maintaining an offset map so spans always reference the original text; Arabic locales match script-preserving. The scan finds all surface-form occurrences and resolves overlaps deterministically — longest span wins, then score tier (preferred > alternate > canonical), then earliest start, then canonical ID — and orders the surviving matches by span start position in the original text.

## Scope

- Normalizer with original-text offset mapping; Latin + Arabic behavior.
- Lexicon scan over all entities/locales of the *stated* locale; overlap resolution rules.
- Complete `MatchReport` / `EntityMatch` types per ADR 0002 (correction and matched-locale fields present, populated by plans 004/005).
- Port of the relevant branch-735 matcher + normalizer tests.

## Out of scope

- Fuzzy matching (004), locale fallback (005), input bounds/perf (007).

## Dependencies

002 — foundations (lexicon model, typed API, CI gate).
