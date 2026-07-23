# CONTEXT — lexiqr glossary

The project's ubiquitous language. Code, docs, plans, and issues use these terms with exactly these meanings.

## Actors

- **Integrating developer** — backend engineer who pip-installs lexiqr, initializes it with a tenant's lexicon, and calls `transform()` inside their service.
- **Lexicon author** — tenant admin, customer-success engineer, or localization specialist who writes and maintains a tenant's lexicon; works only with the lexicon file, its JSON Schema, and the CLI — never Python.
- **Maintainer** — owns CI, tests, versioning, changelog, and PyPI publishing (solo; everything unattended).
- **OSS contributor** — external developer working from the public repo (minimal support pre-1.0).

## Domain nouns

- **Tenant** — one customer of the integrating developer's SaaS. One `EntityResolver` instance = one tenant's lexicon; tenant→instance mapping is the host application's job.
- **Lexicon** — a tenant's multilingual mapping from jargon to canonical entities; a JSON document (or Python dict) conforming to the versioned lexicon schema.
- **Entity** — a canonical database concept the backend actually queries (e.g. `product`). In lexiqr an entity is just its **canonical ID** — never storage, never a row.
- **Surface form** — a word or phrase a tenant's users actually type for an entity, per locale: preferred (singular/plural) or alternate labels. "flooff" is a preferred de-DE surface form of `product`.
- **Canonical ID** — the stable identifier of an entity (`product`); what a match resolves *to*.
- **Prompt** — the free-form user text handed to `transform()`. lexiqr never guesses its language; the caller states the locale.
- **Locale** — a BCP 47 tag (`de-DE`). A lexicon declares a default locale; resolution may walk a **fallback chain** (exact locale → same-language variants → declared default).
- **Match report** — the typed result of `transform()`: original prompt, resolved locale, and an ordered list of entity matches.
- **Entity match** — one resolution inside a match report: canonical ID, matched surface form, **character span** in the original text, **score tier**, applied **correction** (if fuzzy), and the locale that actually matched.
- **Score tier** — the deterministic ranking of match quality: preferred > alternate > canonical.
- **Span** — start/end character offsets into the *original* prompt text, valid even when normalization stripped accents.
- **Correction** — the fuzzy-match record showing what misspelling was mapped to which surface form ("floof" → "flooff") within the **edit budget** (length-aware maximum edit distance).
- **Normalization** — the deterministic text preparation pass: casefolding, accent stripping for Latin-script locales, script preservation for Arabic.
- **Schema version** — the version of the lexicon file format a document declares (`schemaVersion`) and core pins.
- **Flooff scenario** — the founding example: a German tenant's lexicon mapping "flooff" (and the typo "floof") to `product`; the README quickstart and a CI test.

## Pipeline vocabulary (branch-735 heritage)

The deterministic core pipeline, in order: **normalize → lexicon scan → fuzzy pass → match report**. The branch-735 test suite preserved in `.claude/plan/` is the behavioral spec.

## Containers

- **core** — resolution engine + public API (`EntityResolver`, `transform()`).
- **cli** — `lexiqr validate`, `lexiqr try`; may only call core's public API.
- **schema** — the published, versioned JSON Schema for lexicon files.
- **delivery** — CI quality gates and the tag→publish pipeline.

## Guarantees (capability language)

- **Determinism** — same lexicon + prompt + configuration ⇒ identical result across runs and platforms; a tested guarantee, not an aspiration.
- **Performance envelope** — CI-enforced: `transform()` p95 < 10 ms on a 1,000-surface-form lexicon; initialization < 1 s.
- **Bounded input handling** — empty, oversized, or adversarial Unicode input gets a bounded-time response, never a hang or crash.
