"""C14 made executable: `lexiqr validate` surfaces the load-time error's facts.

Parity holds *by construction* — there is exactly one validation code path
(ADR 0002), so the error an author sees from `validate` is the error an
integrating developer catches at load time. This test guards the **rendering**
of that error: for every invalid fixture it captures the structured
`ValidationError` core raises, runs `validate` on the same file, and asserts the
rendered output carries the same facts — the offending entity, locale, and
field.

The comparison is on facts, not formatting: only the coordinate *values* are
checked for presence, so the renderer's wording and layout may evolve without
this test becoming a change-detector. If the two paths ever diverge in the
facts they surface, it fails.

The corpus is epic #2's real invalid-lexicon set (`schema/fixtures/invalid/`),
not a parallel CLI-only one — the same fixtures the loader is validated against.
"""

import json
from pathlib import Path

import pytest

from conftest import REPO_ROOT
from lexiqr import EntityResolver, Lexicon, ValidationError
from lexiqr.cli import EXIT_INVALID_LEXICON, main

INVALID_CORPUS = REPO_ROOT / "schema" / "fixtures" / "invalid"


def invalid_fixtures() -> list[Path]:
    return sorted(INVALID_CORPUS.glob("*.lexicon.json"))


def load_time_error(fixture: Path) -> ValidationError:
    """The structured error the public API raises for `fixture`, at load time."""
    document = json.loads(fixture.read_text(encoding="utf-8"))
    with pytest.raises(ValidationError) as raised:
        EntityResolver.from_dict(document)
    return raised.value


@pytest.mark.parametrize(
    "fixture",
    invalid_fixtures(),
    ids=lambda p: p.name.removesuffix(".lexicon.json"),
)
def test_validate_output_carries_the_same_facts_as_the_load_time_error(
    fixture: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    captured_error = load_time_error(fixture)

    code = main(["validate", str(fixture)])
    rendered = capsys.readouterr().err

    # The same code path ran, not a CLI-level failure: this really is the
    # lexicon error being rendered.
    assert code == EXIT_INVALID_LEXICON

    facts = {
        "entity": captured_error.canonical_id,
        "locale": captured_error.locale,
        "field": captured_error.field,
    }
    for coordinate, value in facts.items():
        if value is None:
            continue
        assert value in rendered, (
            f"{fixture.stem}: the {coordinate} {value!r} the loader faults is "
            f"absent from what `validate` rendered"
        )


def test_a_file_that_is_not_json_is_reported_in_the_librarys_own_words(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Parity covers the file itself, not only the lexicon inside it.

    "Not valid JSON" is one sentence, written once, in core's loading path. What
    the author reads is that sentence under the shell's prefix — nothing
    re-worded, nothing re-classified — so it cannot drift from what an
    integrating developer catches.
    """
    path = tmp_path / "truncated.lexicon.json"
    path.write_text('{"schemaVersion": "1",', encoding="utf-8")

    with pytest.raises(ValidationError) as raised:
        Lexicon.from_file(str(path))
    library_wording = raised.value.message

    code = main(["validate", str(path)])
    rendered = capsys.readouterr().err

    # A CLI-level failure — the file never became a lexicon to be invalid.
    assert code != EXIT_INVALID_LEXICON
    assert rendered.rstrip("\n") == f"lexiqr: {library_wording}"


def test_the_parity_test_actually_drives_the_shared_invalid_corpus() -> None:
    """Guards the guard: an empty or moved corpus must not pass vacuously."""
    names = {path.name.removesuffix(".lexicon.json") for path in invalid_fixtures()}
    assert {"missing-preferred-singular", "malformed-locale-tag"} <= names
