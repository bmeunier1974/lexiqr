"""The release workflow, read as a declaration of how a tag reaches PyPI.

This is the delivery contract's riskiest step, so it is pinned the way the PR
gate is: by reading `release.yml` and asserting what it promises. The point is
that publishing targets *real* PyPI via trusted publishing with no long-lived
token, that a bad tag can never reach the publish job, and that "the workflow
was green" and "the package installs and works" are made the same statement by a
post-publish job that installs from PyPI and reproduces the flooff match.
"""

from typing import Any, cast

import pytest
import yaml

from conftest import REPO_ROOT

RELEASE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release.yml"


@pytest.fixture
def workflow() -> dict[str, Any]:
    return cast(
        "dict[str, Any]", yaml.safe_load(RELEASE_WORKFLOW.read_text(encoding="utf-8"))
    )


@pytest.fixture
def raw() -> str:
    return RELEASE_WORKFLOW.read_text(encoding="utf-8")


def test_publish_targets_real_pypi_not_testpypi(
    workflow: dict[str, Any], raw: str
) -> None:
    publish = workflow["jobs"]["publish"]

    assert publish["environment"] == "pypi"
    # The flip ADR 0004 designed for: nothing anywhere still points at TestPyPI.
    assert "test.pypi.org" not in raw


def test_publishing_uses_trusted_publishing_with_no_long_lived_token(
    workflow: dict[str, Any], raw: str
) -> None:
    publish = workflow["jobs"]["publish"]

    assert publish["permissions"]["id-token"] == "write"
    steps = publish["steps"]
    assert any("pypa/gh-action-pypi-publish" in step.get("uses", "") for step in steps)
    # No password / API token is introduced — OIDC is the only credential.
    assert "password:" not in raw
    assert "secrets." not in raw


def test_a_bad_tag_cannot_reach_build_or_publish(workflow: dict[str, Any]) -> None:
    jobs = workflow["jobs"]

    assert jobs["build"]["needs"] == "consistency"
    assert jobs["publish"]["needs"] == "build"
    assert jobs["verify"]["needs"] == "publish"


def test_the_publish_step_does_not_skip_an_existing_version(raw: str) -> None:
    """A re-run of an already-published version must fail cleanly, not silently
    skip into a confusing partial state."""
    assert "skip-existing: false" in raw


def test_the_verify_job_installs_from_real_pypi_with_propagation_retry(
    workflow: dict[str, Any], raw: str
) -> None:
    verify = workflow["jobs"]["verify"]
    script = "\n".join(step.get("run", "") for step in verify["steps"])

    assert "pip install" in script
    assert "pypi.org/simple" in script or "--index-url" not in script
    # Tolerates PyPI's index-propagation delay rather than assuming immediacy.
    assert "attempt" in script and "sleep" in script


def test_the_verify_job_reproduces_flooff_and_calls_the_console_entry_point(
    workflow: dict[str, Any],
) -> None:
    verify = workflow["jobs"]["verify"]
    script = "\n".join(step.get("run", "") for step in verify["steps"])

    assert "reproduce_flooff.py" in script  # C1: the published artifact resolves
    assert "/clean-venv/bin/lexiqr" in script  # the console entry point is callable
