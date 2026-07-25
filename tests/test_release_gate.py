"""The release gate's reproduce step, run the way the release workflow runs it."""

import subprocess
import sys

from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "reproduce_flooff.py"


def test_the_install_verification_script_reproduces_the_flooff_match() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], capture_output=True, text=True
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "product" in result.stdout
