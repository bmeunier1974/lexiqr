# lexiqr

lexiqr is a deterministic Python library for B2B SaaS backend teams whose tenants each speak their own private language. A tenant defines a multilingual lexicon mapping their company jargon ("flooff") to canonical database entities ("product"); lexiqr initializes from that lexicon and transforms free-form prompts into entity-identified prompt objects — exact and typo-tolerant matches with character spans, scores, and corrections. Where teams today hardcode synonym tables, retrain embeddings, or let an LLM guess, lexiqr is a pip-installable resolution layer that is deterministic, explainable, and tenant-scoped. Published on PyPI, public on GitHub, production-ready from v1.0.

## Problem

Backend engineers building multi-tenant search and AI features face tenants with private, company-specific vocabulary: a German media company calls every movie a "flooff", but the backend searches a `product` entity. Today these teams hardcode per-tenant synonym tables into application code, retrain embeddings per tenant, or let an LLM guess the mapping — expensive, non-deterministic, and unmaintainable as tenants and locales multiply. There is no off-the-shelf, deterministic, tenant-scoped layer that resolves jargon in a user's prompt to the database entities the backend actually queries.

## Actors

- **Integrating developer** — backend engineer who pip-installs lexiqr, initializes it with a tenant's lexicon, and calls `transform()` inside their service; wants a small, typed, predictable API.
- **Lexicon author** — tenant admin, customer-success engineer, or localization specialist who writes and maintains a tenant's multilingual lexicon; interacts through the lexicon file format, its schema, and its validation tooling — never through Python code.
- **Maintainer/releaser** — owns CI, tests, versioning, changelog, and PyPI publishing for the public package.
- **OSS contributor** — external developer who clones the public repo to reproduce, fix, or extend (minimal support in v1; full contributor experience is post-1.0).

## Capabilities

- **C1** — An integrating developer can install the package from PyPI into a clean Python ≥3.10 environment with `pip install lexiqr`.
- **C2** — An integrating developer can initialize a lexicon instance from structured multilingual lexicon data (JSON file or Python dict) conforming to lexiqr's versioned entity schema: each entity has a canonical ID plus per-locale surface forms (preferred singular/plural, alternate labels).
- **C3** — An integrating developer supplying invalid lexicon data gets precise, human-readable validation errors identifying the offending entity, locale, and field.
- **C4** — An integrating developer can call `transform(prompt, locale)` and receive a typed match report: the original prompt, the resolved locale, and an ordered list of entity matches, each with canonical entity ID, matched surface form, character span in the original text, and score tier (preferred > alternate > canonical).
- **C5** — An integrating developer observes typo-tolerant matching: a misspelled surface form (e.g. "floof" for "flooff") still resolves, within length-aware edit budgets, and the match report shows the applied correction; fuzzy matching can be disabled via configuration.
- **C6** — An integrating developer can configure a locale fallback chain at initialization (default: exact locale → same-language variants → lexicon's declared default), and the match report states which locale actually matched.
- **C7** — An integrating developer sees accent-insensitive matching for Latin-script locales (diacritics stripped, spans still aligned to the original text) and script-preserving matching for Arabic.
- **C8** — An integrating developer calling `transform()` with empty, oversized, or adversarial Unicode input gets a bounded-time response with a clear result or error — never a hang or crash.
- **C9** — An integrating developer running the same lexicon, prompt, and configuration gets an identical result across runs and platforms — determinism is a tested guarantee.
- **C10** — An integrating developer gets full type hints (`py.typed`): IDE completion works and the package passes strict type-checking as a dependency.
- **C11** — An integrating developer can rely on a stated, CI-enforced performance envelope: `transform()` p95 under 10 ms against a 1,000-surface-form lexicon; initialization under 1 second.
- **C12** — An integrating developer can follow the README quickstart to reproduce the founding scenario — a German tenant's lexicon mapping "flooff" (and the typo "floof") to the `product` entity — in under 5 minutes.
- **C13** — A lexicon author can validate their lexicon file against a published, versioned JSON Schema using standard tooling, without installing anything from lexiqr.
- **C14** — A lexicon author can run `lexiqr validate my-lexicon.json` and get the same precise, human-readable errors the library raises at load time.
- **C15** — A lexicon author can run `lexiqr try my-lexicon.json --locale de-DE "wo ist flooff"` and see the full match report in the terminal, without writing Python.
- **C16** — A maintainer sees every pull request automatically run lint (ruff), strict type-check (mypy), and the test suite across Python 3.10–3.13.
- **C17** — A maintainer can cut a release by pushing a version tag: CI builds the distribution and publishes it to PyPI via trusted publishing (no long-lived tokens), with semver and a changelog entry per release.
- **C18** — An OSS contributor can clone the public GitHub repo, set up the dev environment with one command (`uv sync`), and run the full test suite locally.

## Non-goals

- **LLM filter building and search-definition validation** — turning detected entities into search filters stays in consuming services.
- **HTTP server / FastAPI wrapper** — lexiqr is a library; services wrap it themselves.
- **Language detection** — the caller states the prompt's locale.
- **Built-in multi-tenant registry** — one instance = one tenant's lexicon; tenant→instance mapping is the host application's job (documented as a recipe, not code).
- **Semantic, embedding, or NER-based matching** — lexiqr matches the lexicon deterministically, nothing more.
- **Lexicon authoring UI** — authors work with files, the JSON Schema, and the CLI.
- **Hot reload** — a changed lexicon means creating a new instance; no file watching.
- **Persistence or database access** — lexiqr never touches storage; the "DB entity" is just a canonical ID.
- **Full contributor experience in v1** — CONTRIBUTING.md, issue/PR templates, and fork CI are deliberately post-1.0.

## Constraints

- **Runtime**: Python ≥3.10; test matrix 3.10–3.13. Single runtime dependency: rapidfuzz (prebuilt wheels on all mainstream platforms). CLI uses stdlib argparse only.
- **License**: MIT.
- **Behavioral spec**: the deterministic core's observable contract (spans, score tiers, overlap resolution, normalization, determinism) is specified by this repository's own test suite.
- **Tooling**: uv-managed development environment; GitHub Actions for CI and releases.
- **Team**: solo maintainer; everything must run unattended (automated releases, CI as the quality gate).

## Success criteria

- `pip install lexiqr` succeeds from a clean environment; the installed v1.0 was produced by the automated tag→publish pipeline; the GitHub repo is public with a green CI badge.
- The README quickstart reproduces the flooff scenario (including the "floof" typo correction) copy-paste in under 5 minutes, and that example runs as a test in CI.
- The performance envelope holds in CI: `transform()` p95 < 10 ms on a 1,000-surface-form lexicon; initialization < 1 s.
