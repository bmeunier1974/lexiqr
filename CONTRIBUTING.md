# Contributing to lexiqr

## Dev environment

Two steps — [uv](https://docs.astral.sh/uv/) does the rest:

```bash
git clone https://github.com/bmeunier1974/lexiqr.git && cd lexiqr
uv sync          # creates the venv and installs lexiqr plus its dev tools
uv run pytest    # the same suite CI runs on every push and pull request
```

## The pull-request gate

Every pull request gets three verdicts. They are exactly these commands, and
their configuration lives in `pyproject.toml`, so a green run locally means a
green run in CI:

```bash
uv run ruff check . && uv run ruff format --check .   # lint
uv run mypy                                           # strict type-check
uv run pytest                                         # tests
```

CI runs the test leg on **Python 3.10, 3.11, 3.12 and 3.13** — the versions the
package advertises. Locally, `uv run --python 3.10 pytest` reproduces any single
version. Nothing merges red.

Trying the CLI by hand:

```bash
uv run lexiqr try examples/flooff.lexicon.json --locale de-DE "wo ist flooff"
```

## Releasing

The full step-by-step checklist — including the human judgments CI cannot make —
lives in [RELEASING.md](RELEASING.md). The summary:

Releases are cut by pushing a semver tag; `.github/workflows/release.yml` builds
the wheel and sdist, publishes them, then installs the published package into a
clean virtualenv and reproduces the flooff match. A release that cannot be
installed and reproduced fails.

```bash
git tag vX.Y.Z && git push origin vX.Y.Z
```

Publishing targets **real PyPI** via trusted publishing — no long-lived token
ever exists in the repository or its secrets; the workflow exchanges a
short-lived OIDC token for upload rights (ADR 0004). The one-time pending-publisher
registration and the human release prerequisites are in [RELEASING.md](RELEASING.md).
