"""Discoverability and usage errors: the CLI teaches itself to an author.

An author who reads no documentation must be able to discover both commands and
each command's arguments from `--help`, and a wrong or missing argument must be
correctable rather than alarming — a usage message and argparse's conventional
exit code, never a stack trace. Output stays plain text, legible over SSH and in
a CI log.
"""

import pytest

from lexiqr.cli import main

USAGE_EXIT_CODE = 2  # argparse's own conventional code


def test_top_level_help_lists_both_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])

    out = capsys.readouterr().out
    assert exit_info.value.code == 0
    assert "validate" in out
    assert "try" in out


def test_validate_help_names_the_lexicon_argument(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["validate", "--help"])

    out = capsys.readouterr().out
    assert exit_info.value.code == 0
    assert "lexicon" in out.lower()


def test_try_help_names_lexicon_locale_and_prompt(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["try", "--help"])

    out = capsys.readouterr().out
    assert exit_info.value.code == 0
    assert "lexicon" in out.lower()
    assert "locale" in out.lower()
    assert "prompt" in out.lower()


def test_a_missing_argument_prints_usage_and_exits_with_the_usage_code(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["validate"])  # the lexicon path is required

    err = capsys.readouterr().err
    assert exit_info.value.code == USAGE_EXIT_CODE
    assert "usage" in err.lower()
    assert "Traceback" not in err


def test_try_missing_required_locale_is_a_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["try", "some.json", "wo ist flooff"])  # no --locale

    err = capsys.readouterr().err
    assert exit_info.value.code == USAGE_EXIT_CODE
    assert "usage" in err.lower()
    assert "locale" in err.lower()


def test_an_unknown_command_is_a_usage_error_not_a_crash(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["frobnicate", "some.json"])

    err = capsys.readouterr().err
    assert exit_info.value.code == USAGE_EXIT_CODE
    assert "Traceback" not in err


def test_no_command_at_all_is_a_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main([])

    assert exit_info.value.code == USAGE_EXIT_CODE
