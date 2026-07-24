"""`lexiqr try <file> --locale <loc> "<prompt>"`, exercised in-process.

Covers the whole command: a prompt that matches, a prompt that matches nothing,
an invalid lexicon, a missing file, and malformed JSON — asserting the streams
and the exit code on each. `try` loads through the same path `validate` does, so
an invalid lexicon is a load failure with rendered validation errors, never a
confusing matching failure; and no-match is a distinct exit code from any load
failure.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from lexiqr.cli import (
    EXIT_CLI_ERROR,
    EXIT_INVALID_LEXICON,
    EXIT_NO_MATCH,
    EXIT_OK,
    main,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
FLOOFF = REPO_ROOT / "examples" / "flooff.lexicon.json"


def valid_document() -> Any:
    return json.loads(FLOOFF.read_text(encoding="utf-8"))


def write(tmp_path: Path, document: Any) -> Path:
    path = tmp_path / "lexicon.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_try_prints_the_match_report_on_stdout_and_exits_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["try", str(FLOOFF), "--locale", "de-DE", "wo ist flooff"])

    captured = capsys.readouterr()
    assert code == EXIT_OK
    assert "product" in captured.out
    assert "[flooff]" in captured.out  # the span, marked against the prompt
    assert captured.err == ""


def test_try_on_a_prompt_that_matches_nothing_says_so_and_exits_nonzero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["try", str(FLOOFF), "--locale", "de-DE", "nichts hier"])

    captured = capsys.readouterr()
    assert code == EXIT_NO_MATCH
    assert code != EXIT_OK
    assert "no match" in captured.out.lower()
    assert captured.err == ""


def test_try_on_an_invalid_lexicon_renders_validation_errors_not_a_match_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    document = valid_document()
    del document["entities"]["product"]["locales"]["de-DE"]["preferred"]["singular"]
    path = write(tmp_path, document)

    code = main(["try", str(path), "--locale", "de-DE", "wo ist flooff"])

    captured = capsys.readouterr()
    assert code == EXIT_INVALID_LEXICON
    assert captured.out == ""
    assert "preferred.singular" in captured.err


def test_the_load_failure_code_is_distinct_from_the_no_match_code(
    tmp_path: Path,
) -> None:
    document = valid_document()
    document["schemaVersion"] = "99"
    invalid = main(["try", str(write(tmp_path, document)), "--locale", "de-DE", "x"])

    no_match = main(["try", str(FLOOFF), "--locale", "de-DE", "nichts"])

    assert invalid != no_match
    assert invalid == EXIT_INVALID_LEXICON
    assert no_match == EXIT_NO_MATCH


def test_try_on_a_missing_file_is_a_cli_level_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(
        ["try", str(tmp_path / "absent.json"), "--locale", "de-DE", "wo ist flooff"]
    )

    captured = capsys.readouterr()
    assert code == EXIT_CLI_ERROR
    assert captured.out == ""
    assert "absent.json" in captured.err


def test_try_on_malformed_json_is_a_cli_level_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{ not json", encoding="utf-8")

    code = main(["try", str(path), "--locale", "de-DE", "wo ist flooff"])

    captured = capsys.readouterr()
    assert code == EXIT_CLI_ERROR
    assert captured.out == ""
    assert "JSON" in captured.err
