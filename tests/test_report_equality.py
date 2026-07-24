"""The report-equality gate, exercised in the ordinary test run.

The cross-platform matrix job runs `scripts/report_equality.py --check` on every
OS × Python cell; this test runs the same check in the normal suite, so a change
that shifts resolution output is caught on the contributor's own machine before
it ever reaches the matrix — and so the golden can never silently rot.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "report_equality.py"


def test_resolution_matches_the_cross_platform_golden() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
