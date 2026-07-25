"""Make the release-tooling scripts importable from the test suite.

`scripts/` is not a package — the release workflow runs each file as a plain
script — but the release-consistency gate is a *pure* module whose whole point
is being unit-testable against crafted inputs rather than only observable by
pushing real tags. Putting the scripts directory on the path lets a test import
that checker directly, without the subprocess indirection the I/O-bound scripts
(reproduce_flooff, report_equality) are exercised through.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
