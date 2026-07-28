# lexiqr

[![CI](https://github.com/bmeunier1974/lexiqr/actions/workflows/ci.yml/badge.svg)](https://github.com/bmeunier1974/lexiqr/actions/workflows/ci.yml)
[![Python versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-3776AB?logo=python&logoColor=white)](https://github.com/bmeunier1974/lexiqr/blob/main/pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Typing: strict](https://img.shields.io/badge/mypy-strict-blue)](https://mypy-lang.org/)
[![Linted with Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Built with uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
<!-- After the first PyPI release, add the dynamic badges:
[![PyPI](https://img.shields.io/pypi/v/lexiqr)](https://pypi.org/project/lexiqr/)
[![PyPI - Python versions](https://img.shields.io/pypi/pyversions/lexiqr)](https://pypi.org/project/lexiqr/)
and drop the static Python-versions badge above. -->

**lexiqr** is a deterministic Python library for B2B SaaS backend teams whose tenants each speak their own private language. A tenant defines a multilingual lexicon mapping their company jargon ("flooff") to canonical database entities ("product"); lexiqr initializes from that lexicon and transforms free-form prompts into entity-identified prompt objects — exact and typo-tolerant matches with character spans, scores, and corrections.

Where teams today hardcode synonym tables, retrain embeddings, or let an LLM guess, lexiqr is a pip-installable resolution layer that is **deterministic, explainable, and tenant-scoped**.

## Highlights

- **Deterministic by contract** — the same lexicon, prompt, and configuration produce an identical result across runs, platforms, and Pythons; a tested guarantee, not an aspiration.
- **Typo-tolerant, explainably** — length-aware edit budgets, and every fuzzy match carries the correction it applied; turn the pass off entirely with `fuzzy=False`.
- **Multilingual** — per-locale surface forms, locale fallback chains, accent-insensitive matching for Latin scripts, script-preserving matching for Arabic.
- **Spans you can trust** — character offsets always index the text the user typed, never a normalized copy.
- **Entries with metadata** — several terms resolve to one entity, each carrying a tenant-defined filter verbatim, so a match report replaces the per-tenant lookup table in your service.
- **Typed, tested, bounded** — `py.typed` and strict-mypy clean; a canonical, round-tripping report serialization; documented input limits; a CI-enforced performance envelope.
- **A CLI for lexicon authors** — `lexiqr validate` and `lexiqr try` work without writing Python, with exit codes a script can branch on.

## Installation

Requires **Python 3.10+**. The wheel is pure Python with a single runtime
dependency ([RapidFuzz](https://github.com/rapidfuzz/RapidFuzz)):

```bash
pip install lexiqr
```

or, with [uv](https://docs.astral.sh/uv/):

```bash
uv add lexiqr
```

## Quickstart

A lexicon maps one tenant's private jargon to canonical entities. Here a German
tenant maps **flooff** to the `product` entity — this is the file the examples
below run against:

<!-- quickstart:file lexicon.json -->
```json
{
  "schemaVersion": "1",
  "defaultLocale": "de-DE",
  "entities": {
    "product": {
      "locales": {
        "de-DE": { "preferred": { "singular": "flooff" } }
      }
    }
  }
}
```

Resolve a prompt in Python. Typo tolerance is on by default, so the typo
`floof` still resolves and the match carries a correction naming what was typed:

<!-- quickstart:python -->
```python
from lexiqr import EntityResolver

resolver = EntityResolver.from_file("lexicon.json")

# "flooff" resolves to the product entity, with its character span and tier.
match = resolver.transform("wo ist flooff", locale="de-DE").matches[0]
print(
    f"{match.canonical_id} <- {match.surface_form!r} at {match.span}, tier {match.score_tier.value}"
)

# The typo "floof" still resolves; the match names what was typed.
typo = resolver.transform("wo ist floof", locale="de-DE").matches[0]
print(f"corrected {typo.correction!r} -> {typo.surface_form!r}")
```

<!-- quickstart:expected -->
```text
product <- 'flooff' at (7, 13), tier preferred
corrected 'floof' -> 'flooff'
```

Lexicon authors don't need Python: the same lexicon checks and runs from the
command line. `lexiqr validate` confirms the file is well-formed —

<!-- quickstart:shell -->
```bash
lexiqr validate lexicon.json
```

<!-- quickstart:expected -->
```text
lexicon.json: valid lexicon.
```

— and `lexiqr try` resolves a prompt against it, showing the same match the
developer sees:

<!-- quickstart:shell -->
```bash
lexiqr try lexicon.json --locale de-DE "wo ist flooff"
```

<!-- quickstart:expected -->
```text
prompt: "wo ist [flooff]"
resolved via: de-DE
1 match:

  [1] product ← "flooff"
      tier: preferred   locale: de-DE   text: "flooff"
```

The `fuzzy` keyword — accepted by `EntityResolver(...)`, `from_file`, and `from_dict`, defaulting to `True` — is public, semver-governed API; pass `fuzzy=False` for exact-only behaviour.

## The whole contract, in one command

The quickstart above is the five-minute story. This is the long one: a single
command that resolves a realistic tenant lexicon and prints twelve narrated
sections, each stating a claim, showing what lexiqr produced, and asserting it.

```bash
uv run python examples/demo.py
```

It **exits non-zero naming the section that failed**, so it is a verification and
not a brochure. Its input is [`examples/medien.lexicon.json`](examples/medien.lexicon.json),
a German media tenant, and the file itself — [`examples/demo.py`](examples/demo.py) —
is one flat file you can read top to bottom and copy a section out of. It imports
nothing but lexiqr and the standard library.

What the twelve sections claim:

1. a tenant lexicon loads from a file — validation *is* construction (**C2**)
2. a rejected lexicon names the entry, locale and field at fault (**C3**)
3. an exact match reports its entity, surface form, span into the original prompt, and score tier (**C4**)
4. preferred, alternate and canonical tiers each resolve and each name their tier (**C4**)
5. two entries resolve to one `product`, each reporting its own entry ID and filter (**C19**)
6. a typo resolves and carries its correction; the same prompt with `fuzzy=False` does not (**C5**)
7. a prompt in an undeclared locale variant resolves through the fallback chain, and the report names the locale that answered (**C6**)
8. accented and unaccented spellings both match with spans still on the typed text; Arabic matches script-preserving (**C7**)
9. two entities in one prompt come back ordered by position, and an overlap resolves to the longest span (**C4**)
10. a prompt over the documented maximum length is refused before any matching; whitespace-only is an empty report, not an error (**C8**)
11. a report round-trips through the canonical serialization and serializes byte-identically twice (**C9**)
12. the same lexicon through `lexiqr validate` and `lexiqr try`, with the exit codes a script reads (**C14**, **C15**)

**Three claims it deliberately does not make**, each owned by a gate of its own —
a transcript this long should not be read as the whole guarantee:

- **the performance envelope** — owned by the CI perf gate (`uv run pytest -m perf`); see [Performance envelope](#performance-envelope) below;
- **cross-platform report equality** — owned by the report-equality matrix job, which compares every OS and Python against `scripts/report_equality.golden.json`;
- **installability from PyPI** — owned by the release workflow's clean-virtualenv leg, which installs the published wheel and runs against it.

An abridged excerpt of the real output — sections 5 and 6, with the other ten
elided. The full transcript is committed as
[`examples/demo.golden.txt`](examples/demo.golden.txt), and the test suite
compares the command's output to it:

<!-- quickstart:skip -->
```text
lexiqr — a sample run: every claim printed, every claim asserted.
lexicon: examples/medien.lexicon.json

--- 5. Two entries resolve to one entity, each with its own filter [C19] ---

match     "zeig mir die filme" → product ← "filme"  span=(13, 18)  tier=preferred
          locale=de-DE  entry=movie  filter={genre=drama|thriller, productType=Movie}
match     "zeig mir die serien" → product ← "serien"  span=(13, 19)  tier=preferred
          locale=de-DE  entry=series  filter={episodic=true, productType=Series}

--- 6. A typo resolves and carries its correction; with fuzzy off it does not [C5] ---

prompt    "zeig mir die flme"
tolerant  product ← "filme"  span=(13, 17)  tier=preferred  locale=de-DE  entry=movie
          filter={genre=drama|thriller, productType=Movie}  correction="flme"
exact     EntityResolver.from_file(..., fuzzy=False) → 0 matches, resolved via de-DE

OK: every section held.
```

## Usage

The quickstart resolves one word. These are the pieces an integrating developer
reaches for next, in the order they usually come up.

### Validating a lexicon on its own

Validation *is* construction: `Lexicon.from_file` (and `from_dict`) either returns
a lexicon lexiqr can trust or raises `ValidationError` naming the entity, locale,
and field at fault. A tenant's file can therefore be checked on the way in — at
deploy time, in an upload handler, in your own tests — without building a
throwaway resolver to find out whether it is valid:

<!-- quickstart:python -->
```python
from lexiqr import Lexicon, ValidationError

try:
    lexicon = Lexicon.from_file("lexicon.json")
except ValidationError as invalid:
    print(f"rejected: {invalid}")
else:
    print(f"valid: {sorted(lexicon.entries)} in {lexicon.default_locale}")
```

<!-- quickstart:expected -->
```text
valid: ['product'] in de-DE
```

A `Lexicon` you already hold goes straight into a resolver —
`EntityResolver(lexicon)` — so nothing is parsed or validated twice.

A file that is not JSON at all raises `MalformedDocumentError`. It *is* a
`ValidationError`, so the `except` above already covers it; catch it by name only
when you need to tell "that file is not a lexicon document" from "that lexicon
says the wrong thing" — the distinction the `lexiqr` CLI turns into its two exit
codes.

### Input limits

`transform()` accepts a prompt of at most **10,000 characters** (Unicode code points), exported as `MAX_PROMPT_LENGTH`. A prompt over that limit raises `ValidationError` — the same structured error every other lexiqr failure raises — before any matching work happens, so a pasted document is rejected cheaply rather than taking a request thread with it. Reject or truncate upstream if your callers can paste arbitrary text.

A single surface form in a lexicon is bounded too: at most **128 characters**, exported as `MAX_SURFACE_FORM_LENGTH`, enforced when the lexicon is loaded rather than when a prompt is matched (see [docs/lexicon-semantic-checks.md](docs/lexicon-semantic-checks.md)). Code that generates labels should size them against that constant rather than against a copy of the number.

Both limits are fixed parts of the contract, not per-call arguments or configuration knobs: two numbers to reason about. Changing either is a semver-visible change.

### Canonical report serialization

`serialize_report(report)` turns a `MatchReport` into a **canonical** string — sorted keys, no insignificant whitespace, pure ASCII, and the match list in the report's own order. Two byte-equal serializations mean two equal reports and nothing else, so you can snapshot a result in your test suite, diff two snapshots to see real behaviour change, or store one and compare it to another months later. `deserialize_report(text)` is its inverse: the form round-trips.

```python
from lexiqr import serialize_report, deserialize_report

snapshot = serialize_report(resolver.transform("wo ist flooff", locale="de-DE"))
# ... store `snapshot`, compare it later, or check it into your tests
```

Both functions are public, semver-governed API: the serialized shape can only change on a major release, so a patch or minor upgrade never silently invalidates a stored snapshot.

### Multi-tenant use

lexiqr resolves one tenant's lexicon per resolver, and deliberately ships **no**
tenant registry — mapping tenants to resolvers is your composition, not lexiqr's,
so it stays a thin layer you control. The recipe is a cache of resolvers keyed by
tenant, each built once from that tenant's lexicon:

<!-- quickstart:skip -->
```python
# Illustrative recipe — not run in CI. Adapt the loader and cache to your stack.
from functools import lru_cache
from pathlib import Path

from lexiqr import EntityResolver, MatchReport


@lru_cache(maxsize=None)
def resolver_for(tenant_id: str) -> EntityResolver:
    """One resolver per tenant, built once and reused across requests."""
    lexicon = Path("lexicons") / f"{tenant_id}.lexicon.json"
    return EntityResolver.from_file(lexicon)


def resolve(tenant_id: str, prompt: str, locale: str) -> MatchReport:
    return resolver_for(tenant_id).transform(prompt, locale)
```

Because a resolver is built once and then only read, one instance per tenant is
safe to share across requests; size the cache to your tenant count, or swap
`lru_cache` for whatever eviction your deployment already uses.

## Performance envelope

lexiqr is built to sit in a request path, so its performance is a stated, CI-enforced contract, measured against the seeded **1,000-surface-form** benchmark lexicon:

- **`transform()` p95 < 10 ms**
- **initialization < 1 second** (cold)

**How it is measured** (so you can reproduce it): initialization is timed cold — one resolver built once, nothing warmed. `transform()` p95 excludes warm-up — a fixed set of warm-up calls is discarded, then p95 is taken over a fixed number of timed iterations against the benchmark lexicon. A long-but-under-limit prompt is measured too, so the 10,000-character size limit is the only performance cliff, not a hidden one before it.

**The gate vs. the guarantee.** The numbers above are the guarantee. The CI perf gate asserts the envelope multiplied by a **3× headroom factor** (p95 < 30 ms, init < 3 s) on a single fixed runner: shared CI runners are noisy, and the headroom turns that noise into a re-run rather than a false failure. A change has to make matching roughly an order of magnitude slower to trip the gate — catching subtle drift is not its job, which is why the raw timings are also recorded, un-gated, on every run.

## Versioning and compatibility

lexiqr runs on **Python 3.10, 3.11, 3.12, and 3.13**, and follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). A stored snapshot or
a version constraint is only as trustworthy as the surface the promise covers, so
that surface is named explicitly. Semver governs:

- **The public API** — everything exported from the `lexiqr` package:
  `EntityResolver` and its `from_file` / `from_dict` / `transform` methods,
  including the `fuzzy` keyword.
- **The lexicon model** — `Lexicon`, the type `EntityResolver` takes, with its
  validating `from_file` / `from_dict` constructors; `Entry`, the named set of
  surface forms an entity is keyed by, with the entity it resolves to and the
  filter it carries; `SurfaceForms`, the shape an entry holds per locale; and
  `Metadata` / `MetadataValue`, that filter and the values it may hold.
- **The structured error types** — `ValidationError` and its coordinates
  (`canonical_id`, `locale`, `field`), which the CLI renders verbatim, and
  `MalformedDocumentError`, the `ValidationError` subclass raised when a file is
  not JSON at all.
- **The match report types** — `MatchReport`, `EntityMatch`, and `ScoreTier`,
  and the fields a caller reads off them (span, tier, correction, the entry that
  answered, and its metadata).
- **The canonical report serialization** — the byte-level shape produced by
  `serialize_report` and consumed by `deserialize_report`.
- **The two documented limits** — `MAX_PROMPT_LENGTH` and
  `MAX_SURFACE_FORM_LENGTH`, whose values are part of the contract.

A breaking change to any of these is a major-version change. Everything else —
internal modules, private helpers, log wording — can change in a patch. Read the
[CHANGELOG](CHANGELOG.md) before upgrading; every release documents what changed.

## Repository layout

This is a single-repo project: it is both the meta-repo (vision and blueprint) and the product repo (all four C4 containers ship from here as one wheel).

| Path | Container | What it is |
|------|-----------|------------|
| `src/lexiqr/` (excl. `cli/`) | **core** | The deterministic resolution engine and public typed API |
| `src/lexiqr/cli/` | **cli** | `lexiqr validate` / `lexiqr try` for lexicon authors |
| `schema/` | **schema** | The versioned JSON Schema for lexicon files, plus the shared fixture corpus |
| `.github/workflows/`, `pyproject.toml` | **delivery** | CI gates and tag→PyPI trusted publishing |

## Documentation

Guides for using lexiqr:

- [docs/lexicon-authoring.md](docs/lexicon-authoring.md) — writing and validating a lexicon
  file, the `lexiqr validate` / `lexiqr try` CLI, and its scriptable exit-code contract
- [docs/matching-rules.md](docs/matching-rules.md) — normalization, spans, score tiers,
  overlap resolution and ordering: the behavior determinism makes public
- [docs/lexicon-semantic-checks.md](docs/lexicon-semantic-checks.md) — the complete list of
  checks core enforces beyond the published schema, and why
- [CHANGELOG.md](CHANGELOG.md) — every release, recorded by hand

The project's cross-container truth:

- [VISION.md](VISION.md) — problem, actors, capabilities, non-goals, constraints
- [CONTEXT.md](CONTEXT.md) — the project glossary
- [docs/adr/](docs/adr/) — architecture decision records (repo shape, contracts)

## Contributing

Two steps, no setup document to drift out of date — [uv](https://docs.astral.sh/uv/) does the rest:

```bash
git clone https://github.com/bmeunier1974/lexiqr.git && cd lexiqr
uv sync          # creates the venv and installs lexiqr plus its dev tools
uv run pytest    # the same suite CI runs on every push and pull request
```

The pull-request gate (lint, strict type-check, tests on every supported
Python) is described in [CONTRIBUTING.md](CONTRIBUTING.md); the release
process, including the one-time PyPI trusted-publisher registration, lives in
[RELEASING.md](RELEASING.md). To report a security issue, see
[SECURITY.md](SECURITY.md).

## License

MIT — see [LICENSE](LICENSE).
