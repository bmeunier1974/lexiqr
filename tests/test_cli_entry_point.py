"""The `lexiqr` console entry point, exercised across the real process boundary."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "examples" / "flooff.lexicon.json"
)


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
    result = run_cli("try", str(FIXTURE_PATH), "--locale", "de-DE", "wo ist flooff")

    assert result.returncode == 0
    assert "product" in result.stdout
    assert "flooff" in result.stdout


def test_the_cli_reaches_only_for_lexiqrs_public_api() -> None:
    """ADR 0002: the cli↔core boundary is the public API, checked by construction.

    Every reference into lexiqr from any CLI module must resolve either to the
    package root (`from lexiqr import ...`, the public API) or to a sibling
    module inside the `lexiqr.cli` package itself. A reach into a private core
    submodule (`from lexiqr.matcher import ...`) fails here, not at review time.
    """
    cli_package = Path(__file__).resolve().parent.parent / "src" / "lexiqr" / "cli"

    private_imports: list[str] = []
    for module in sorted(cli_package.rglob("*.py")):
        for line in module.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped.startswith(("from lexiqr.", "import lexiqr.")):
                continue
            target = stripped.split()[1]
            if target == "lexiqr.cli" or target.startswith("lexiqr.cli."):
                continue
            private_imports.append(f"{module.name}: {stripped}")

    assert private_imports == []
