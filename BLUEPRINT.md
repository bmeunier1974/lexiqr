# Blueprint — lexiqr

Derived from [VISION.md](VISION.md).

All containers live in this single repository (`lexiqr`) and ship as one wheel; they are containers in the C4 sense — separately runnable/publishable artifacts with hard boundaries — not separate deployments. Public API entry point: `from lexiqr import EntityResolver`.

## Containers

### core

- **Responsibility:** The deterministic resolution engine and public typed API: lexicon loading and validation, normalization (accent stripping, script preservation), exact + fuzzy matching with length-aware edit budgets, locale fallback chains, and `EntityResolver.transform(prompt, locale)` returning the typed match report.
- **Not responsible for:** Terminal UX (that's `cli`), defining the public lexicon file format (that's `schema` — core *implements* validation against it), packaging or publishing (that's `delivery`).
- **Tech:** Python ≥3.10, rapidfuzz as the sole runtime dependency, `py.typed` — the vision's runtime constraints verbatim. Ports the proven branch-735 pipeline (normalize → lexicon scan → fuzzy pass → match report); its test suite in `.claude/plan/` is the behavioral spec.
- **Repo:** this repo — `src/lexiqr/` (excluding `cli.py`)

### cli

- **Responsibility:** The no-Python interface for lexicon authors: `lexiqr validate <file>` and `lexiqr try <file> --locale <loc> "<prompt>"`, rendering core's validation errors and match reports in the terminal.
- **Not responsible for:** Any matching, validation, or formatting *logic* — it may only call core's public API (the same one integrating developers use). This boundary is what guarantees C14's error parity by construction.
- **Tech:** stdlib argparse only (vision constraint), shipped as a console entry point in the same wheel.
- **Repo:** this repo — `src/lexiqr/cli.py`

### schema

- **Responsibility:** The versioned, published JSON Schema for lexicon files — the source of truth for the lexicon format, usable with standard JSON Schema tooling without installing lexiqr.
- **Not responsible for:** Runtime validation error messages (core's job) or schema *evolution tooling* (migrations are out of scope for v1).
- **Tech:** JSON Schema draft 2020-12. Lives in-repo at `schema/lexicon.v1.schema.json`; `$id` points at the raw.githubusercontent.com URL of a tagged path, so versions are immutable by construction and require zero infrastructure.
- **Repo:** this repo — `schema/`

### delivery

- **Responsibility:** The unattended quality gate and release pipe: PR CI (ruff, strict mypy, tests across Python 3.10–3.13, perf envelope check, determinism check), tag→publish via PyPI trusted publishing (no long-lived tokens), semver + changelog, and the one-command dev environment (`uv sync`).
- **Not responsible for:** Anything at runtime; no code in the wheel.
- **Tech:** GitHub Actions + uv + a modern build backend (hatchling). Skeleton publishes to TestPyPI; the real PyPI target is switched on once the pipe is proven.
- **Repo:** this repo — `.github/workflows/`, `pyproject.toml`

## Contracts

### cli ↔ core

- **Protocol:** In-process Python calls, restricted to core's *public* API surface — nothing from private modules.
- **Operations:** load-and-validate a lexicon (raising structured validation errors), construct an `EntityResolver`, call `transform(prompt, locale)`.
- **Data shapes:** `Lexicon` input (dict/JSON per schema v1); `ValidationError` carrying entity ID, locale, and field (C3); `MatchReport` carrying original prompt, resolved locale, and ordered `EntityMatch` list (canonical ID, matched surface form, character span, score tier, applied correction, matched locale).

### core ↔ schema

- **Protocol:** Shared document format — the lexicon JSON. Core pins the schema version it implements; lexicon files declare theirs in a `schemaVersion` field.
- **Operations:** none at runtime (core never fetches the schema); the contract is *equivalence* — a file that passes the published JSON Schema must load in core, and core's stricter semantic checks (e.g. duplicate surface forms) are documented as beyond-schema.
- **Data shapes:** lexicon document — schema version, default locale, entities keyed by canonical ID, per-locale surface forms (preferred singular/plural, alternate labels).

### delivery ↔ core / cli / schema

- **Protocol:** GitHub Actions triggers (PR, `v*` tag push).
- **Operations:** on PR — lint, strict type-check, full test suite on 3.10–3.13, perf envelope, determinism check, quickstart-as-test; on tag — build wheel+sdist, publish via trusted publishing (TestPyPI until the pipe is proven, then PyPI), require changelog entry.
- **Data shapes:** semver tag `vX.Y.Z`; the wheel (containing core + cli + bundled schema); CHANGELOG entry per release.

## Walking skeleton

The thinnest deployed path touching all four containers — Plan 001 everywhere:

1. **schema** — `schema/lexicon.v1.schema.json` exists with the minimal shape; a one-entity lexicon file (`product` ← "flooff", locale `de-DE`) validates against it with a standard validator.
2. **core** — `EntityResolver(lexicon)` loads that file; `transform("wo ist flooff", "de-DE")` returns one exact match: entity `product`, surface "flooff", correct character span. (No fuzzy, no fallback, no accents — exact match only.)
3. **cli** — `lexiqr try lexicon.json --locale de-DE "wo ist flooff"` prints that same match report.
4. **delivery** — CI runs the above as tests on one Python version; pushing tag `v0.0.1` builds the wheel and publishes it to **TestPyPI** via trusted publishing; a clean venv `pip install`s it from TestPyPI and reproduces the match.

One interaction proven end to end: *a lexicon file becomes an installed package that resolves "flooff" to `product`.*

## Coverage map

Status lifecycle: `mapped → planned → epic → shipped`.

| Capability | Container(s) | Plan | Epic | Status |
|------------|--------------|------|------|--------|
| C1 — pip install from PyPI | delivery | [008](docs/plans/008-release.md) | | planned |
| C2 — init from lexicon data | core | [002](docs/plans/002-foundations.md) | [lexiqr#2](https://github.com/bmeunier1974/lexiqr/issues/2) | epic |
| C3 — precise validation errors | core | [002](docs/plans/002-foundations.md) | [lexiqr#2](https://github.com/bmeunier1974/lexiqr/issues/2) | epic |
| C4 — transform() match report | core | [003](docs/plans/003-exact-matching.md) | | planned |
| C5 — typo-tolerant matching | core | [004](docs/plans/004-fuzzy-matching.md) | | planned |
| C6 — locale fallback chain | core | [005](docs/plans/005-locale-fallback.md) | | planned |
| C7 — accent/script handling | core | [003](docs/plans/003-exact-matching.md) | | planned |
| C8 — bounded adversarial input | core | [007](docs/plans/007-hardening.md) | | planned |
| C9 — determinism guarantee | core, delivery | [007](docs/plans/007-hardening.md) | | planned |
| C10 — py.typed / strict typing | core, delivery | [002](docs/plans/002-foundations.md) | [lexiqr#2](https://github.com/bmeunier1974/lexiqr/issues/2) | epic |
| C11 — CI-enforced perf envelope | core, delivery | [007](docs/plans/007-hardening.md) | | planned |
| C12 — README quickstart (flooff) | core, delivery | [008](docs/plans/008-release.md) | | planned |
| C13 — published JSON Schema | schema | [002](docs/plans/002-foundations.md) | [lexiqr#2](https://github.com/bmeunier1974/lexiqr/issues/2) | epic |
| C14 — `lexiqr validate` | cli | [006](docs/plans/006-cli.md) | | planned |
| C15 — `lexiqr try` | cli | [006](docs/plans/006-cli.md) | | planned |
| C16 — PR CI (lint/type/test matrix) | delivery | [002](docs/plans/002-foundations.md) | [lexiqr#2](https://github.com/bmeunier1974/lexiqr/issues/2) | epic |
| C17 — tag→PyPI trusted publishing | delivery | [008](docs/plans/008-release.md) | | planned |
| C18 — one-command dev env | delivery | [001](docs/plans/001-walking-skeleton.md) | [lexiqr#1](https://github.com/bmeunier1974/lexiqr/issues/1) | epic |
