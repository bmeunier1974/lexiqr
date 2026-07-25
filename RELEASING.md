# Releasing lexiqr

Releasing is one action — push a version tag — wrapped in a few things a machine
cannot check. This is the whole path from "ready to release" to "published and
verified", written down so a solo maintainer releasing unattended forgets none
of it, and so a contributor can see how a merged change reaches PyPI.

Each step is marked **[CI]** when a machine enforces it, or **[human]** when it
is a judgment only a person can make. The human ones are the point of this
document: CI cannot tell you whether the multi-tenant recipe still matches the
API.

## One-time setup (before the first release)

- **[human] Register the project name and trusted publisher on PyPI.** In the
  PyPI web UI (<https://pypi.org/manage/account/publishing/>), register a
  pending publisher so the workflow can upload without any long-lived token
  (trusted publishing, ADR 0004):

  | Field | Value |
  |-------|-------|
  | PyPI Project Name | `lexiqr` |
  | Owner | `bmeunier1974` |
  | Repository name | `lexiqr` |
  | Workflow name | `release.yml` |
  | Environment name | `pypi` |

  Without this, the publish step is rejected. This is configuration, not code,
  done once. (The skeleton proved the same pipe against TestPyPI first; see
  [CONTRIBUTING.md](CONTRIBUTING.md) → Releasing.)

## The rules the release must satisfy

- **[CI] Semver.** The tag is `vMAJOR.MINOR.PATCH`, optionally with a prerelease
  suffix (`v1.0.0-rc.1`). A breaking change to the semver-governed surface named
  in the [README](README.md#versioning-and-compatibility) is a major bump.
- **[CI] Changelog per release.** Every release has its own non-empty
  [`CHANGELOG.md`](CHANGELOG.md) entry, matching the tag. Move the pending notes
  out of `## [Unreleased]` into a new `## [x.y.z]` heading dated today.
- **[CI] These three must agree.** The release-consistency gate
  (`scripts/release_consistency.py`) is the first job on a `v*` tag: it fails in
  seconds if the tag, the package version in `pyproject.toml`, and the top
  changelog entry disagree, before anything is built. Run it locally first:

  ```bash
  python scripts/release_consistency.py vX.Y.Z
  ```

## Human prerequisites CI cannot verify

- **[human] Multi-tenant recipe review.** The recipe in the
  [README](README.md#multi-tenant-use) is marked non-executable, so CI does not
  run it and cannot catch it drifting from the API. Re-read it against the
  current public surface before releasing — this is the one deliverable with no
  automated drift guard.

## Cutting the release

1. **[human]** Bump `version` in `pyproject.toml` to `X.Y.Z`.
2. **[human]** Move `## [Unreleased]` notes into a new `## [X.Y.Z] - <date>`
   entry in `CHANGELOG.md`.
3. **[CI]** Confirm the working tree is green: `uv run pytest`, `uv run mypy`,
   `uv run ruff check .`.
4. **[human]** Run the consistency gate locally (command above).
5. **[human]** Confirm the human prerequisites above.
6. **[human]** Tag and push:

   ```bash
   git tag vX.Y.Z && git push origin vX.Y.Z
   ```

7. **[CI]** The `release.yml` workflow runs: consistency gate → build → publish
   to PyPI via trusted publishing → install from real PyPI into a clean
   virtualenv and reproduce the flooff match. A release that cannot be installed
   and reproduced fails.

## If a release fails

- The gate rejected the tag: fix the disagreement it named, delete the tag
  (`git push origin :vX.Y.Z`), and re-tag. No version number was burned.
- The publish failed because the version already exists on PyPI: bump to the
  next patch and release again. PyPI versions are immutable and cannot be
  re-uploaded.
