"""`lexiqr validate <file>`, exercised in-process across the whole command.

These capture the streams and assert the exit code on every path: a valid
lexicon, an invalid one, a missing file, and a file that is not JSON. Two error
families are kept visibly distinct — the shell's own CLI-level failures (path /
JSON) versus core's structured lexicon errors — and each family carries its own
exit code.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from conftest import FLOOFF_LEXICON, flooff_document
from lexiqr.cli import main


def write(tmp_path: Path, document: Any) -> Path:
    path = tmp_path / "lexicon.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_validate_confirms_a_valid_lexicon_on_stdout_and_exits_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["validate", str(FLOOFF_LEXICON)])

    captured = capsys.readouterr()
    assert code == 0
    assert "valid" in captured.out.lower()
    assert captured.err == ""


def test_validate_reports_an_invalid_lexicon_on_stderr_and_exits_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    document = flooff_document()
    del document["entities"]["product"]["locales"]["de-DE"]["preferred"]["singular"]
    path = write(tmp_path, document)

    code = main(["validate", str(path)])

    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""
    assert "product" in captured.err
    assert "de-DE" in captured.err
    assert "preferred.singular" in captured.err


def test_validate_on_a_missing_file_gives_a_distinct_cli_level_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "nope.lexicon.json"

    code = main(["validate", str(missing)])

    captured = capsys.readouterr()
    assert code != 0
    assert code != 1  # a CLI-level failure, not a lexicon error
    assert captured.out == ""
    assert "nope.lexicon.json" in captured.err
    assert "invalid lexicon" not in captured.err.lower()


def test_validate_on_malformed_json_is_distinct_from_a_schema_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{ this is not json", encoding="utf-8")

    code = main(["validate", str(path)])

    captured = capsys.readouterr()
    assert code != 0
    assert code != 1
    assert captured.out == ""
    assert "JSON" in captured.err
    assert "invalid lexicon" not in captured.err.lower()


def test_missing_file_and_bad_json_share_one_distinguishable_exit_code(
    tmp_path: Path,
) -> None:
    missing_code = main(["validate", str(tmp_path / "absent.json")])

    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    broken_code = main(["validate", str(broken)])

    assert missing_code == broken_code
    assert missing_code not in (0, 1)


def test_an_invalid_lexicon_is_a_different_exit_code_than_a_cli_level_failure(
    tmp_path: Path,
) -> None:
    document = flooff_document()
    document["schemaVersion"] = "99"
    invalid_code = main(["validate", str(write(tmp_path, document))])

    cli_level_code = main(["validate", str(tmp_path / "absent.json")])

    assert invalid_code != cli_level_code
