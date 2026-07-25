"""The `lexiqr` console entry point, exercised across the real process boundary."""

import ast
import shutil
import subprocess
import sys

import pytest

import lexiqr
from conftest import FLOOFF_LEXICON, REPO_ROOT


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "lexiqr.cli", *args],
        capture_output=True,
        text=True,
    )


def test_lexiqr_console_script_runs_and_reports_usage() -> None:
    result = run_cli("--help")

    assert result.returncode == 0
    assert "lexiqr" in result.stdout


def test_lexiqr_is_installed_as_a_console_entry_point() -> None:
    executable = shutil.which("lexiqr")
    if executable is None:
        pytest.skip("lexiqr console script not on PATH in this environment")

    result = subprocess.run(
        [executable, "try", "--help"], capture_output=True, text=True
    )

    assert result.returncode == 0


def test_lexiqr_try_prints_the_match_report_and_exits_zero() -> None:
    result = run_cli("try", str(FLOOFF_LEXICON), "--locale", "de-DE", "wo ist flooff")

    assert result.returncode == 0
    assert "product" in result.stdout
    assert "flooff" in result.stdout


def test_the_cli_reaches_only_for_lexiqrs_documented_public_api() -> None:
    """ADR 0002: the cli↔core boundary is the documented public API, statically.

    Every reference into lexiqr from any CLI module must resolve to a name in
    ``lexiqr.__all__`` (the semver-governed public API), or to a sibling module
    inside the ``lexiqr.cli`` package itself. A name that is not exported, or a
    reach into a private core submodule (``from lexiqr.matcher import ...``),
    fails here on the first offence rather than at review time.
    """
    cli_package = REPO_ROOT / "src" / "lexiqr" / "cli"
    public_api = set(lexiqr.__all__)

    violations: list[str] = []
    for module in sorted(cli_package.rglob("*.py")):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                where = node.module or ""
                if where == "lexiqr":
                    violations += [
                        f"{module.name}: from lexiqr import {alias.name}"
                        for alias in node.names
                        if alias.name not in public_api
                    ]
                elif where == "lexiqr.cli" or where.startswith("lexiqr.cli."):
                    continue
                elif where == "lexiqr" or where.startswith("lexiqr."):
                    violations.append(f"{module.name}: from {where} import ...")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if name in {"lexiqr", "lexiqr.cli"} or name.startswith(
                        "lexiqr.cli."
                    ):
                        continue
                    if name.startswith("lexiqr"):
                        violations.append(f"{module.name}: import {name}")

    assert violations == []
