# lexiqr

**lexiqr** is a deterministic Python library for B2B SaaS backend teams whose tenants each speak their own private language. A tenant defines a multilingual lexicon mapping their company jargon ("flooff") to canonical database entities ("product"); lexiqr initializes from that lexicon and transforms free-form prompts into entity-identified prompt objects — exact and typo-tolerant matches with character spans, scores, and corrections.

Where teams today hardcode synonym tables, retrain embeddings, or let an LLM guess, lexiqr is a pip-installable resolution layer that is **deterministic, explainable, and tenant-scoped**.

```bash
pip install lexiqr
```

```python
from lexiqr import EntityResolver

resolver = EntityResolver.from_file("lexicon.json")
report = resolver.transform("wo ist flooff", locale="de-DE")
# → one match: entity "product", surface "flooff", span (7, 13), tier "preferred"

# Typo tolerance is on by default: "floof" still resolves, and the match carries
# a correction naming what was typed. Pass fuzzy=False for exact-only behaviour.
exact_only = EntityResolver.from_file("lexicon.json", fuzzy=False)
```

The `fuzzy` keyword — accepted by `EntityResolver(...)`, `from_file`, and `from_dict`, defaulting to `True` — is public, semver-governed API.

> **Status:** pre-1.0 — under active development. The API above is the target contract.

## Input limits

`transform()` accepts a prompt of at most **10,000 characters** (Unicode code points). A prompt over that limit raises `ValidationError` — the same structured error every other lexiqr failure raises — before any matching work happens, so a pasted document is rejected cheaply rather than taking a request thread with it. Reject or truncate upstream if your callers can paste arbitrary text.

This limit is a fixed part of the contract, not a per-call argument or a configuration knob: one number to reason about. Changing it is a semver-visible change.

## Canonical report serialization

`serialize_report(report)` turns a `MatchReport` into a **canonical** string — sorted keys, no insignificant whitespace, pure ASCII, and the match list in the report's own order. Two byte-equal serializations mean two equal reports and nothing else, so you can snapshot a result in your test suite, diff two snapshots to see real behaviour change, or store one and compare it to another months later. `deserialize_report(text)` is its inverse: the form round-trips.

```python
from lexiqr import serialize_report, deserialize_report

snapshot = serialize_report(resolver.transform("wo ist flooff", locale="de-DE"))
# ... store `snapshot`, compare it later, or check it into your tests
```

Both functions are public, semver-governed API: the serialized shape can only change on a major release, so a patch or minor upgrade never silently invalidates a stored snapshot.

## Performance envelope

lexiqr is built to sit in a request path, so its performance is a stated, CI-enforced contract, measured against the seeded **1,000-surface-form** benchmark lexicon:

- **`transform()` p95 < 10 ms**
- **initialization < 1 second** (cold)

**How it is measured** (so you can reproduce it): initialization is timed cold — one resolver built once, nothing warmed. `transform()` p95 excludes warm-up — a fixed set of warm-up calls is discarded, then p95 is taken over a fixed number of timed iterations against the benchmark lexicon. A long-but-under-limit prompt is measured too, so the 10,000-character size limit is the only performance cliff, not a hidden one before it.

**The gate vs. the guarantee.** The numbers above are the guarantee. The CI perf gate asserts the envelope multiplied by a **3× headroom factor** (p95 < 30 ms, init < 3 s) on a single fixed runner: shared CI runners are noisy, and the headroom turns that noise into a re-run rather than a false failure. A change has to make matching roughly an order of magnitude slower to trip the gate — catching subtle drift is not its job, which is why the raw timings are also recorded, un-gated, on every run.

## This repository

This is a single-repo project: it is both the meta-repo (vision and blueprint) and the product repo (all four C4 containers ship from here as one wheel).

| Path | Container | What it is |
|------|-----------|------------|
| `src/lexiqr/` (excl. `cli/`) | **core** | The deterministic resolution engine and public typed API |
| `src/lexiqr/cli/` | **cli** | `lexiqr validate` / `lexiqr try` for lexicon authors |
| `schema/` | **schema** | The versioned JSON Schema for lexicon files, plus the shared fixture corpus |
| `.github/workflows/`, `pyproject.toml` | **delivery** | CI gates and tag→PyPI trusted publishing |

Cross-container truth lives at the root:

- [VISION.md](VISION.md) — problem, actors, capabilities, non-goals, constraints
- [BLUEPRINT.md](BLUEPRINT.md) — container decomposition, contracts, walking skeleton, coverage map
- [CONTEXT.md](CONTEXT.md) — the project glossary
- [docs/adr/](docs/adr/) — architecture decision records (repo shape, contracts)
- [docs/plans/](docs/plans/) — dependency-ordered implementation plans
- [docs/lexicon-authoring.md](docs/lexicon-authoring.md) — writing and validating a lexicon
  file, the `lexiqr validate` / `lexiqr try` CLI, and its scriptable exit-code contract
- [docs/lexicon-semantic-checks.md](docs/lexicon-semantic-checks.md) — the complete list of
  checks core enforces beyond the published schema, and why
- [docs/matching-rules.md](docs/matching-rules.md) — normalization, spans, score tiers,
  overlap resolution and ordering: the behavior determinism makes public

## Contributing

Two steps, no setup document to drift out of date — [uv](https://docs.astral.sh/uv/) does the rest:

```bash
git clone https://github.com/bmeunier1974/lexiqr.git && cd lexiqr
uv sync          # creates the venv and installs lexiqr plus its dev tools
uv run pytest    # the same suite CI runs on every push and pull request
```

Release process and the one-time TestPyPI publisher registration live in
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
