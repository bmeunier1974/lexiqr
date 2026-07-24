"""The quickstart extractor, driven against crafted markdown.

The extractor is the single fragile place where "the README is the test" is made
real: it turns markdown into the runnable units a test will execute, and it must
never guess. A block runs only because it was *marked* to run; an illustrative
snippet is left alone; a README that marks nothing fails loudly rather than
passing vacuously — a quickstart test that silently collects nothing is the
exact rot this design exists to prevent. These tests pin that contract on
crafted markdown, so the next story can point it at the real README with
confidence.
"""

import json
from pathlib import Path

import pytest
from quickstart_extractor import (
    QuickstartExtractionError,
    extract_quickstart,
    materialize_files,
)


def test_a_marked_python_block_is_collected_as_a_python_unit() -> None:
    markdown = "# Title\n\n<!-- quickstart:python -->\n```python\nprint('hello')\n```\n"

    quickstart = extract_quickstart(markdown)

    assert len(quickstart.units) == 1
    unit = quickstart.units[0]
    assert unit.kind == "python"
    assert unit.code == "print('hello')\n"


def test_unmarked_blocks_are_illustrative_and_excluded() -> None:
    markdown = (
        "Install it:\n"
        "\n"
        "```bash\n"
        "pip install lexiqr\n"  # illustrative — no directive, must not be collected
        "```\n"
        "\n"
        "<!-- quickstart:shell -->\n"
        "```bash\n"
        "lexiqr try lexicon.json --locale de-DE 'wo ist flooff'\n"
        "```\n"
    )

    quickstart = extract_quickstart(markdown)

    assert len(quickstart.units) == 1
    assert quickstart.units[0].kind == "shell"
    assert "lexiqr try" in quickstart.units[0].code


def test_markdown_with_no_executable_blocks_raises() -> None:
    markdown = (
        "# Title\n\nProse only, plus an illustrative block:\n\n"
        "```python\nnothing_here_is_marked()\n```\n"
    )

    with pytest.raises(QuickstartExtractionError):
        extract_quickstart(markdown)


def test_expected_output_attaches_to_the_preceding_unit() -> None:
    markdown = (
        "<!-- quickstart:shell -->\n"
        "```bash\n"
        "lexiqr try lexicon.json --locale de-DE 'wo ist flooff'\n"
        "```\n"
        "<!-- quickstart:expected -->\n"
        "```text\n"
        "product <- 'flooff' at (7, 13)\n"
        "```\n"
    )

    quickstart = extract_quickstart(markdown)

    assert len(quickstart.units) == 1  # the expected block is not itself a unit
    assert quickstart.units[0].expected_output == "product <- 'flooff' at (7, 13)\n"


def test_expected_output_without_a_preceding_unit_raises() -> None:
    markdown = "<!-- quickstart:expected -->\n```text\norphan\n```\n"

    with pytest.raises(QuickstartExtractionError):
        extract_quickstart(markdown)


# --- inline files: the lexicon a reader copies is the lexicon CI runs ---

_WITH_LEXICON = """\
<!-- quickstart:file lexicon.json -->
```json
{"schemaVersion": "1.0", "entities": []}
```

<!-- quickstart:python -->
```python
from lexiqr import EntityResolver
EntityResolver.from_file("lexicon.json")
```
"""


def test_a_file_directive_captures_path_and_content_and_is_not_a_unit() -> None:
    quickstart = extract_quickstart(_WITH_LEXICON)

    assert len(quickstart.units) == 1  # the json block is a file, not a unit
    assert len(quickstart.files) == 1
    assert quickstart.files[0].path == "lexicon.json"
    assert '"schemaVersion": "1.0"' in quickstart.files[0].content


def test_materialize_files_writes_them_relative_to_a_root(tmp_path: Path) -> None:
    quickstart = extract_quickstart(_WITH_LEXICON)

    materialize_files(quickstart, tmp_path)

    written = tmp_path / "lexicon.json"
    assert written.exists()
    assert json.loads(written.read_text()) == {"schemaVersion": "1.0", "entities": []}
