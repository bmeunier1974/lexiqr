"""The release-consistency gate — the first thing a version tag hits.

Pushing `v1.0.0` sets three things in motion that must already agree: the tag
itself, the version the package declares, and the entry the changelog records.
If they don't, the choices are to ship a wheel labelled with the wrong version
or to burn the version number on a failed build — both worse than refusing the
tag. This gate refuses it, in seconds, before anything is built.

The decision is a pure function of three strings. `check_release_consistency`
takes the tag, the declared version, and the changelog's top entry, and returns
agreement or a single, specific disagreement that names which of the three was
wrong and what each said. The workflow does the I/O — reading the tag from the
push, the version from the package, the top entry from `CHANGELOG.md` — and
hands the values here; the module only decides. That split is what makes every
case a real tag could hit a crafted unit test rather than something you can only
see by pushing.

Run as a script, it does that I/O itself and exits non-zero on disagreement,
printing the same message, so the release workflow's gate job is one line.

## Semver and the changelog-per-release rule

lexiqr follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html): the
tag is `vMAJOR.MINOR.PATCH`, optionally with a prerelease suffix
(`v1.0.0-rc.1`) for a release candidate. Every release — prerelease included —
carries its own `CHANGELOG.md` entry, written by hand, non-empty, and matching
the tag. This gate is the enforcement: no tag ships whose three coordinates
disagree, and no release ships undocumented, by construction.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

#: The official SemVer 2.0.0 grammar (semver.org), anchored. It accepts a
#: prerelease suffix (`-rc.1`) and build metadata (`+build.5`) so a release
#: candidate is a well-formed tag, not a malformed one.
_SEMVER = re.compile(
    r"^(?P<core>(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*))"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


@dataclass(frozen=True)
class ChangelogEntry:
    """The changelog's top released entry: the version it names and its body.

    The body is the prose beneath the version heading; an entry whose body is
    empty or only whitespace is a release nobody documented, which the gate
    rejects as surely as a version mismatch.
    """

    version: str
    body: str


@dataclass(frozen=True)
class ConsistencyResult:
    """Agreement, or the one reason the tag is being refused."""

    ok: bool
    message: str


def check_release_consistency(
    tag: str,
    package_version: str,
    changelog: ChangelogEntry | None,
) -> ConsistencyResult:
    """Decide whether a tag may ship. Pure: three values in, a verdict out."""
    tag_version = _tag_version(tag)

    if _SEMVER.match(tag_version) is None:
        return ConsistencyResult(
            ok=False,
            message=(
                f"malformed tag: {tag!r} is not a semver version tag. Expected "
                f"vMAJOR.MINOR.PATCH, optionally with a prerelease suffix "
                f"(e.g. v1.0.0 or v1.0.0-rc.1)."
            ),
        )

    if tag_version != package_version:
        return ConsistencyResult(
            ok=False,
            message=(
                f"tag/version mismatch: the tag says {tag_version!r} but the "
                f"package declares version {package_version!r}."
            ),
        )

    if changelog is None:
        return ConsistencyResult(
            ok=False,
            message=(
                f"missing changelog entry: the changelog has no released entry "
                f"for {tag_version!r}. Every release is documented by "
                f"construction — add its CHANGELOG.md entry before tagging."
            ),
        )

    if changelog.version != tag_version:
        return ConsistencyResult(
            ok=False,
            message=(
                f"tag/changelog mismatch: the tag says {tag_version!r} but the "
                f"changelog's top entry is for {changelog.version!r}."
            ),
        )

    if not changelog.body.strip():
        return ConsistencyResult(
            ok=False,
            message=(
                f"empty changelog entry: the changelog has an entry for "
                f"{tag_version!r} but its body is empty. A release with nothing "
                f"written about it is not documented — describe the change."
            ),
        )

    return ConsistencyResult(ok=True, message=f"{tag} is consistent.")


def _tag_version(tag: str) -> str:
    """The version a tag carries: the tag with its leading `v` removed."""
    return tag[1:] if tag.startswith("v") else tag


_TABLE_HEADING = re.compile(r"^\s*\[(?P<table>[^\]]+)\]\s*$")
_VERSION_ASSIGNMENT = re.compile(r"""^\s*version\s*=\s*["'](?P<version>[^"']+)["']""")


def read_project_version(pyproject_text: str) -> str:
    """The version pyproject declares, from `[project]` and nowhere else.

    Deliberately a hand rolled read of the one line that matters rather than a
    TOML parse: it keeps this module stdlib-only and 3.10-clean (no `tomllib`,
    which is 3.11+), and the gate only needs `[project].version`. The `[project]`
    scoping matters — a `version` under some `[tool.*]` table is not the
    package's version and must not be mistaken for it.
    """
    in_project = False
    for line in pyproject_text.splitlines():
        table = _TABLE_HEADING.match(line)
        if table is not None:
            in_project = table.group("table").strip() == "project"
            continue
        if in_project:
            assignment = _VERSION_ASSIGNMENT.match(line)
            if assignment is not None:
                return assignment.group("version")
    raise ValueError("pyproject.toml declares no [project] version")


#: A Keep-a-Changelog version heading: `## [1.0.0] - 2026-07-24`. The date is
#: optional here — the gate cares about the version and the body, not the date.
_VERSION_HEADING = re.compile(r"^##\s+\[(?P<version>[^\]]+)\]")


def parse_top_entry(changelog_text: str) -> ChangelogEntry | None:
    """The changelog's top *released* entry, or None if there isn't one yet.

    Keep-a-Changelog keeps an `## [Unreleased]` section at the top for pending
    work; a release moves those notes down under a versioned heading. The tag
    must match that first versioned heading — not Unreleased, which names no
    version — so this skips it and returns the first real release, its body
    being everything up to the next `## ` heading. Before the first release the
    changelog holds only Unreleased, and this returns None: the gate reads that
    as a missing entry.
    """
    lines = changelog_text.splitlines()
    for i, line in enumerate(lines):
        heading = _VERSION_HEADING.match(line)
        if heading is None:
            continue
        version = heading.group("version").strip()
        if version.lower() == "unreleased":
            continue
        body_lines: list[str] = []
        for body_line in lines[i + 1 :]:
            if body_line.startswith("## "):
                break
            body_lines.append(body_line)
        return ChangelogEntry(version=version, body="\n".join(body_lines))
    return None


def main(argv: list[str]) -> int:
    """The gate as the workflow runs it: read the three values, print, exit.

    The tag comes from the first argument, or `GITHUB_REF_NAME` when the release
    workflow runs on a tag push. The version comes from `pyproject.toml` and the
    top entry from `CHANGELOG.md`. Everything the decision needs is read here so
    the checker itself stays pure; a disagreement exits non-zero with the same
    message a unit test would see.
    """
    tag = argv[1] if len(argv) > 1 else os.environ.get("GITHUB_REF_NAME", "")
    if not tag:
        print("no tag given (pass one as an argument or set GITHUB_REF_NAME)")
        return 2

    version = read_project_version((_REPO_ROOT / "pyproject.toml").read_text())
    changelog_path = _REPO_ROOT / "CHANGELOG.md"
    changelog = (
        parse_top_entry(changelog_path.read_text()) if changelog_path.exists() else None
    )

    result = check_release_consistency(tag, version, changelog)
    print(result.message)
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
