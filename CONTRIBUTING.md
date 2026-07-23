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

Releases are cut by pushing a semver tag; `.github/workflows/release.yml` builds
the wheel and sdist, publishes them, then installs the published package into a
clean virtualenv and reproduces the flooff match. A release that cannot be
installed and reproduced fails.

```bash
git tag v0.0.1 && git push origin v0.0.1
```

Publishing currently targets **TestPyPI**; the switch to real PyPI is a one-line
change to `repository-url`, made once the pipe is proven.

### One-time prerequisite: register the pending publisher

**Before the first tag push**, the maintainer must register a *pending publisher*
on TestPyPI, or the publish step is rejected. This is configuration, not code —
it is done once, by hand, in the TestPyPI web UI
(<https://test.pypi.org/manage/account/publishing/>):

| Field | Value |
|-------|-------|
| PyPI Project Name | `lexiqr` |
| Owner | `bmeunier1974` |
| Repository name | `lexiqr` |
| Workflow name | `release.yml` |
| Environment name | `testpypi` |

Trusted publishing means no long-lived token ever exists in the repository or
its secrets: the workflow exchanges a short-lived OIDC token for upload rights
(ADR 0004).
