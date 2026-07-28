"""The release-consistency gate, driven directly against crafted inputs.

The gate is a pure function: it takes the three things a release must agree on
— the pushed tag, the package's declared version, and the changelog's top entry
— and returns agreement or a specific disagreement naming which of the three
disagreed and what each said. Because it is I/O-free, every case a real tag push
could hit is a crafted triple here, asserted on the *message* it produces — the
message is the feature; a gate whose failure needs log archaeology gets disabled
by the person it was built to protect.
"""

import subprocess
import sys

from release_consistency import (
    ChangelogEntry,
    check_release_consistency,
    parse_top_entry,
    read_project_version,
)

from conftest import REPO_ROOT


def test_full_agreement_is_ok() -> None:
    result = check_release_consistency(
        tag="v1.0.0",
        package_version="1.0.0",
        changelog=ChangelogEntry(version="1.0.0", body="- Added the resolver."),
    )

    assert result.ok


def test_tag_disagreeing_with_package_version_names_both() -> None:
    result = check_release_consistency(
        tag="v1.0.0",
        package_version="1.0.1",
        changelog=ChangelogEntry(version="1.0.0", body="- Added the resolver."),
    )

    assert not result.ok
    assert "version" in result.message.lower()
    assert "1.0.0" in result.message  # what the tag said
    assert "1.0.1" in result.message  # what the package declared


def test_malformed_tag_is_rejected_with_a_clear_message() -> None:
    result = check_release_consistency(
        tag="v1.2",
        package_version="1.2",
        changelog=ChangelogEntry(version="1.2", body="- Something."),
    )

    assert not result.ok
    assert "malformed" in result.message.lower()
    assert "v1.2" in result.message  # the offending tag, named


def test_tag_disagreeing_with_changelog_names_both() -> None:
    result = check_release_consistency(
        tag="v1.0.0",
        package_version="1.0.0",
        changelog=ChangelogEntry(version="0.9.0", body="- The previous release."),
    )

    assert not result.ok
    assert "changelog" in result.message.lower()
    assert "1.0.0" in result.message  # what the tag said
    assert "0.9.0" in result.message  # what the changelog's top entry said


def test_missing_changelog_entry_is_rejected() -> None:
    result = check_release_consistency(
        tag="v1.0.0",
        package_version="1.0.0",
        changelog=None,
    )

    assert not result.ok
    assert "changelog" in result.message.lower()
    assert "1.0.0" in result.message  # the version that went undocumented


def test_present_but_empty_changelog_entry_is_rejected() -> None:
    result = check_release_consistency(
        tag="v1.0.0",
        package_version="1.0.0",
        changelog=ChangelogEntry(version="1.0.0", body="   \n  \n"),
    )

    assert not result.ok
    assert "empty" in result.message.lower()
    assert "1.0.0" in result.message


def test_prerelease_tag_that_agrees_is_ok() -> None:
    result = check_release_consistency(
        tag="v1.0.0-rc.1",
        package_version="1.0.0-rc.1",
        changelog=ChangelogEntry(version="1.0.0-rc.1", body="- First candidate."),
    )

    assert result.ok


def test_prerelease_tag_disagreeing_with_version_is_rejected() -> None:
    # A prerelease must still agree with the package — the suffix is not a wildcard.
    result = check_release_consistency(
        tag="v1.0.0-rc.2",
        package_version="1.0.0-rc.1",
        changelog=ChangelogEntry(version="1.0.0-rc.2", body="- Second candidate."),
    )

    assert not result.ok
    assert "rc.2" in result.message
    assert "rc.1" in result.message


# --- parsing the changelog into its top released entry (still pure) ---

_CHANGELOG = """\
# Changelog

## [Unreleased]

### Added
- Something pending.

## [1.0.0] - 2026-07-24

### Added
- The resolver.
- The CLI.

## [0.9.0] - 2026-07-01

### Added
- The walking skeleton.
"""


def test_parse_top_entry_skips_unreleased_and_returns_the_first_release() -> None:
    entry = parse_top_entry(_CHANGELOG)

    assert entry is not None
    assert entry.version == "1.0.0"
    assert "The resolver." in entry.body
    assert "The CLI." in entry.body
    assert "walking skeleton" not in entry.body  # the next release's body, not this one


def test_parse_top_entry_returns_none_when_only_unreleased_exists() -> None:
    text = "# Changelog\n\n## [Unreleased]\n\n### Added\n- Pending.\n"

    assert parse_top_entry(text) is None


# --- reading the declared version out of pyproject (stdlib-only, no toml dep) ---


def test_read_project_version_finds_the_project_table_version() -> None:
    pyproject = (
        "[project]\n"
        'name = "lexiqr"\n'
        'version = "1.2.3"\n'
        'requires-python = ">=3.10"\n'
        "\n"
        "[tool.something]\n"
        'version = "9.9.9"\n'  # a decoy in another table, must not win
    )

    assert read_project_version(pyproject) == "1.2.3"


# --- the script's I/O glue, exercised end to end against the real repo ---

_SCRIPT = REPO_ROOT / "scripts" / "release_consistency.py"


def test_script_reports_a_version_mismatch_against_the_real_repo() -> None:
    # An impossible tag disagrees with whatever the package actually declares, and
    # the script — which reads pyproject and CHANGELOG itself — must say so and
    # exit non-zero. Kept version-independent so it survives release bumps.
    result = subprocess.run(
        [sys.executable, str(_SCRIPT), "v99.99.99"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "99.99.99" in result.stdout
    assert "mismatch" in result.stdout.lower()
