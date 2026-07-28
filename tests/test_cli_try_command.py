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

from conftest import FLOOFF_LEXICON, REPO_ROOT, flooff_document, lexicon_document
from lexiqr import Lexicon
from lexiqr.cli import (
    EXIT_CLI_ERROR,
    EXIT_INVALID_LEXICON,
    EXIT_NO_MATCH,
    EXIT_OK,
    main,
)

#: A lexicon using the entry model: "movie" and "series" both `product`, each with
#: the filter that tells them apart.
MEDIEN_SHARED_ENTITY = (
    REPO_ROOT / "schema" / "fixtures" / "valid" / "medien-shared-entity.lexicon.json"
)


def write(tmp_path: Path, document: Any) -> Path:
    path = tmp_path / "lexicon.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_try_prints_the_match_report_on_stdout_and_exits_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["try", str(FLOOFF_LEXICON), "--locale", "de-DE", "wo ist flooff"])

    captured = capsys.readouterr()
    assert code == EXIT_OK
    assert "product" in captured.out
    assert "[flooff]" in captured.out  # the span, marked against the prompt
    assert captured.err == ""


def test_try_on_a_prompt_that_matches_nothing_says_so_and_exits_nonzero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["try", str(FLOOFF_LEXICON), "--locale", "de-DE", "nichts hier"])

    captured = capsys.readouterr()
    assert code == EXIT_NO_MATCH
    assert code != EXIT_OK
    assert "no match" in captured.out.lower()
    assert captured.err == ""


def test_try_on_an_invalid_lexicon_renders_validation_errors_not_a_match_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    document = flooff_document()
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
    document = flooff_document()
    document["schemaVersion"] = "99"
    invalid = main(["try", str(write(tmp_path, document)), "--locale", "de-DE", "x"])

    no_match = main(["try", str(FLOOFF_LEXICON), "--locale", "de-DE", "nichts"])

    assert invalid != no_match
    assert invalid == EXIT_INVALID_LEXICON
    assert no_match == EXIT_NO_MATCH


def test_try_loads_the_lexicon_exactly_once_per_invocation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """One invocation, one load — counted at the public seam the shell loads through.

    A shell that validated the file and then loaded it again to match would give
    the two passes two different readings of the same path, so "valid" and
    "matched" could describe different lexicons within one run.
    """
    loads: list[str] = []
    load = Lexicon.from_file

    def counted(path: str) -> Lexicon:
        loads.append(path)
        return load(path)

    monkeypatch.setattr(Lexicon, "from_file", counted)

    code = main(["try", str(FLOOFF_LEXICON), "--locale", "de-DE", "wo ist flooff"])

    assert code == EXIT_OK
    assert "flooff" in capsys.readouterr().out
    assert loads == [str(FLOOFF_LEXICON)]


def test_try_matches_against_the_very_lexicon_it_validated(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Matching reuses the loaded lexicon rather than reaching for the file again.

    The seam is made to hand back a lexicon the file does not contain: if the
    report follows that lexicon, matching ran against the object validation
    produced — the two cannot disagree.
    """
    substitute = Lexicon.from_dict(
        lexicon_document("de-DE", widget={"preferred": {"singular": "zork"}})
    )
    monkeypatch.setattr(Lexicon, "from_file", lambda path: substitute)

    code = main(["try", str(FLOOFF_LEXICON), "--locale", "de-DE", "wo ist zork"])

    captured = capsys.readouterr()
    assert code == EXIT_OK
    assert "widget" in captured.out
    assert "product" not in captured.out


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


def test_try_shows_which_entry_answered_and_the_filter_it_carried(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The one place a lexicon author can confirm the discrimination works.

    They never write Python, so `lexiqr try` is where "did my two entries really
    resolve to `product` with different filters?" gets answered.
    """
    code = main(
        [
            "try",
            str(MEDIEN_SHARED_ENTITY),
            "--locale",
            "de-DE",
            "wo sind die filme",
        ]
    )

    captured = capsys.readouterr()
    assert code == EXIT_OK
    assert "product" in captured.out
    assert "entry: movie" in captured.out
    assert "filter: genre=drama|thriller, productType=Movie" in captured.out
    assert captured.err == ""


def test_try_on_a_lexicon_without_the_feature_prints_no_entry_or_filter_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The flooff scenario's output is byte-for-byte what it always was."""
    code = main(["try", str(FLOOFF_LEXICON), "--locale", "de-DE", "wo ist flooff"])

    captured = capsys.readouterr()
    assert code == EXIT_OK
    assert "entry:" not in captured.out
    assert "filter:" not in captured.out
