"""The pull-request gate: what CI promises to check on every change.

These tests read the workflow the way a maintainer reads it — as a declaration
of which verdicts a pull request gets. They deliberately cross-check the gate
against the package's own claims (the Python versions it advertises, the
commands CONTRIBUTING tells a contributor to run) so the gate cannot quietly
drift away from what the project promises.
"""

import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PYPROJECT = REPO_ROOT / "pyproject.toml"


@pytest.fixture
def workflow() -> Any:
    return yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))


def advertised_python_versions() -> list[str]:
    """The Python versions pyproject's classifiers claim support for."""
    prefix = "Programming Language :: Python :: 3."
    return [
        "3." + line.split(prefix, 1)[1].strip().strip('",')
        for line in PYPROJECT.read_text(encoding="utf-8").splitlines()
        if prefix in line
    ]


def all_run_steps(workflow: Any) -> list[str]:
    return [
        step["run"]
        for job in workflow["jobs"].values()
        for step in job["steps"]
        if "run" in step
    ]


def test_the_gate_tests_every_python_version_the_package_advertises(
    workflow: Any,
) -> None:
    versions = advertised_python_versions()
    assert versions == ["3.10", "3.11", "3.12", "3.13"]

    tested = {
        str(version)
        for job in workflow["jobs"].values()
        for version in job.get("strategy", {}).get("matrix", {}).get("python", [])
    }

    assert tested == set(versions)


def test_the_gate_compares_reports_across_operating_systems(workflow: Any) -> None:
    """C9's third layer: a matrix over OS × Python that fails on a platform-
    specific divergence. The gate must carry this dimension, or a report that
    resolves differently on Windows than on Linux would ship unnoticed."""
    os_jobs = [
        job
        for job in workflow["jobs"].values()
        if "os" in job.get("strategy", {}).get("matrix", {})
    ]
    assert os_jobs, "no job runs a matrix over operating systems"

    matrix = os_jobs[0]["strategy"]["matrix"]
    assert {"ubuntu-latest", "macos-latest", "windows-latest"} <= set(matrix["os"])
    assert set(matrix["python"]) == set(advertised_python_versions())
    assert "${{ matrix.os }}" in os_jobs[0]["runs-on"]

    steps = [step["run"] for step in os_jobs[0]["steps"] if "run" in step]
    assert any("report_equality.py" in step for step in steps)


def test_the_gate_lints_with_ruff(workflow: Any) -> None:
    assert any("ruff check" in step for step in all_run_steps(workflow))


def test_the_gate_type_checks_with_mypy_in_strict_mode(workflow: Any) -> None:
    assert any("mypy" in step for step in all_run_steps(workflow))

    pyproject = PYPROJECT.read_text(encoding="utf-8")
    assert "[tool.mypy]" in pyproject
    assert "strict = true" in pyproject


def test_the_gate_runs_on_every_pull_request(workflow: Any) -> None:
    # PyYAML reads the bare key `on:` as the boolean True, so ask for both.
    triggers = workflow.get("on", workflow.get(True))

    assert "pull_request" in triggers


def test_a_contributor_can_run_the_gates_checks_locally(workflow: Any) -> None:
    contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    commands = {"ruff check", "ruff format --check", "mypy", "pytest"}

    for command in commands:
        assert any(command in step for step in all_run_steps(workflow)), command
        assert command in contributing, command


def run_check(tool: list[str], target: Path) -> subprocess.CompletedProcess[str]:
    """Run one of the gate's checks over `target`, with the repo's own config."""
    return subprocess.run(
        ["uv", "run", *tool, str(target)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def test_the_lint_leg_rejects_code_that_violates_the_projects_rules(
    tmp_path: Path,
) -> None:
    offender = tmp_path / "unused_import.py"
    offender.write_text("import os\n", encoding="utf-8")

    result = run_check(["ruff", "check"], offender)

    assert result.returncode != 0, result.stdout


def test_the_type_check_leg_rejects_code_that_does_not_type_check(
    tmp_path: Path,
) -> None:
    offender = tmp_path / "wrong_type.py"
    offender.write_text("def n() -> int:\n    return 'not an int'\n", encoding="utf-8")

    result = run_check(["mypy"], offender)

    assert result.returncode != 0, result.stdout
