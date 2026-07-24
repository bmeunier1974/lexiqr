# Changelog

All notable changes to lexiqr are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
lexiqr adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html):
the release tag is `vMAJOR.MINOR.PATCH`, optionally with a prerelease suffix
(`v1.0.0-rc.1`). **Every release carries its own entry here** — written by hand,
non-empty, and matching the tag. The release-consistency gate
(`scripts/release_consistency.py`) enforces this on every tag push: a tag whose
version disagrees with this file, or that has no entry here, fails before the
package is built. See that module's docstring for the full rule.

Pending changes accumulate under **Unreleased**; cutting a release moves them
down under a new `## [x.y.z]` heading dated on the day it ships.

## [Unreleased]

### Added

- Release-consistency gate: a pure checker (`scripts/release_consistency.py`)
  that refuses a version tag unless the tag, the package's declared version, and
  this changelog's top entry agree, with a message naming which of the three
  disagreed. Runs as the first job on a `v*` tag, before build and publish.
- This changelog, in Keep-a-Changelog format.
