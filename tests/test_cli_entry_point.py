"""The `lexiqr` console entry point declared in pyproject must resolve."""

import subprocess
import sys


def test_lexiqr_console_script_runs_and_reports_usage() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "lexiqr.cli", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "lexiqr" in result.stdout
