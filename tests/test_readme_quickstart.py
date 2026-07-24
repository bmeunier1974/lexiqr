"""The README quickstart, executed — this is the C12 guarantee.

The front page is the founding flooff story, and it is run here exactly as a
reader would run it: the inline lexicon is written to disk, each marked Python
block is executed, each marked CLI block is invoked, and the output is compared
to what the README claims it produces. Because the blocks come out of the actual
README, the quickstart cannot drift from the shipped API — editing the README
can break this test, which is the intended trade: a quickstart that can rot is
worse than one that occasionally fails CI.

The assertion is on *output*, not the absence of an exception. A snippet that ran
but resolved nothing would pass a smoke test; here the `product` match, its span
and tier, the `floof` → `flooff` correction, and the CLI's rendered report are
all compared, which is what makes this a guarantee rather than an import check.
"""

import shlex
import subprocess
import sys
from pathlib import Path

import pytest
from quickstart_extractor import RunnableUnit, extract_quickstart, materialize_files

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"


@pytest.fixture(scope="module")
def quickstart() -> object:
    return extract_quickstart(README.read_text(encoding="utf-8"))


def _normalize(text: str) -> str:
    """Compare output by content, not by trailing spaces or edge blank lines."""
    return "\n".join(line.rstrip() for line in text.strip("\n").splitlines()).strip()


def _run(unit: RunnableUnit, cwd: Path) -> str:
    if unit.kind == "python":
        argv = [sys.executable, "-c", unit.code]
    else:
        tokens = shlex.split(unit.code)
        # The README says `lexiqr …`; run the same CLI as an importable module so
        # the test does not depend on the console script being on PATH.
        assert tokens[0] == "lexiqr", tokens
        argv = [sys.executable, "-m", "lexiqr.cli", *tokens[1:]]

    result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_the_quickstart_has_both_actors_and_asserts_every_block(
    quickstart: object,
) -> None:
    """Guard against a vacuous pass: the story must cover both entry points, and
    no executable block may run unchecked."""
    units = quickstart.units  # type: ignore[attr-defined]

    assert any(u.kind == "python" for u in units), "the developer's path"
    assert any(u.kind == "shell" for u in units), "the lexicon author's path"
    assert all(u.expected_output is not None for u in units), (
        "every block asserts its output; a block with no expected output would "
        "be a smoke test hiding inside the quickstart"
    )


def test_every_quickstart_block_produces_the_output_the_readme_claims(
    quickstart: object, tmp_path: Path
) -> None:
    materialize_files(quickstart, tmp_path)  # type: ignore[arg-type]

    for unit in quickstart.units:  # type: ignore[attr-defined]
        output = _run(unit, tmp_path)
        assert _normalize(output) == _normalize(unit.expected_output), (
            f"{unit.kind} block output does not match the README:\n"
            f"--- got ---\n{output}\n--- expected ---\n{unit.expected_output}"
        )


def test_the_python_path_shows_the_match_and_the_correction(
    quickstart: object, tmp_path: Path
) -> None:
    """The two facts the founding story turns on, asserted by name."""
    materialize_files(quickstart, tmp_path)  # type: ignore[arg-type]
    python_output = "\n".join(
        _run(u, tmp_path)
        for u in quickstart.units  # type: ignore[attr-defined]
        if u.kind == "python"
    )

    assert "product" in python_output
    assert "(7, 13)" in python_output  # the exact-match span
    assert "floof" in python_output and "flooff" in python_output  # the correction
