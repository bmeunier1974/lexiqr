"""The release-facing prose a reader judges lexiqr by before installing.

The executable quickstart proves the code; this guards the claims around it —
the semver surface, the supported runtimes, the changelog link, the CI badge,
and the multi-tenant recipe that must stay illustrative. These are drift guards
on the front page, in the repo's convention of testing load-bearing docs.
"""

from pathlib import Path

from quickstart_extractor import extract_quickstart

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"


def _readme() -> str:
    return README.read_text(encoding="utf-8")


def test_the_semver_governed_surface_is_named() -> None:
    """A version constraint is only as good as the surface it covers, so the
    surface is stated: public API, error types, report types, serialization."""
    text = _readme()

    assert "Semantic Versioning" in text
    assert "public API" in text
    assert "ValidationError" in text
    assert "MatchReport" in text and "EntityMatch" in text and "ScoreTier" in text
    assert "serialize_report" in text and "deserialize_report" in text


def test_the_supported_python_versions_and_changelog_are_stated() -> None:
    text = _readme()

    for version in ("3.10", "3.11", "3.12", "3.13"):
        assert version in text, version
    assert "CHANGELOG.md" in text


def test_a_ci_status_badge_is_present() -> None:
    assert "actions/workflows/ci.yml/badge.svg" in _readme()


def test_the_multi_tenant_recipe_is_present_but_not_executable() -> None:
    """The recipe is illustrative guidance, not a contract: it appears on the
    page but the quickstart extractor must not collect it as a runnable unit,
    so it can drift and be caught at review rather than failing CI."""
    text = _readme()

    assert "Multi-tenant" in text
    assert "resolver_for" in text  # the recipe is actually shown

    collected = "\n".join(unit.code for unit in extract_quickstart(text).units)
    assert "resolver_for" not in collected
    assert "lru_cache" not in collected
