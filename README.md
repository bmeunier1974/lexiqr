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
```

> **Status:** pre-1.0 — under active development. The API above is the target contract.

## This repository

This is a single-repo project: it is both the meta-repo (vision and blueprint) and the product repo (all four C4 containers ship from here as one wheel).

| Path | Container | What it is |
|------|-----------|------------|
| `src/lexiqr/` (excl. `cli.py`) | **core** | The deterministic resolution engine and public typed API |
| `src/lexiqr/cli.py` | **cli** | `lexiqr validate` / `lexiqr try` for lexicon authors |
| `schema/` | **schema** | The versioned JSON Schema for lexicon files |
| `.github/workflows/`, `pyproject.toml` | **delivery** | CI gates and tag→PyPI trusted publishing |

Cross-container truth lives at the root:

- [VISION.md](VISION.md) — problem, actors, capabilities, non-goals, constraints
- [BLUEPRINT.md](BLUEPRINT.md) — container decomposition, contracts, walking skeleton, coverage map
- [CONTEXT.md](CONTEXT.md) — the project glossary
- [docs/adr/](docs/adr/) — architecture decision records (repo shape, contracts)
- [docs/plans/](docs/plans/) — dependency-ordered implementation plans

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
