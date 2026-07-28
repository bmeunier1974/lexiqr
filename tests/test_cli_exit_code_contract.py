"""The exit-code contract is documented where scripters will find it.

The contract turns `lexiqr validate` into a CI tool and `lexiqr try` into a
scriptable regression check, so the numbers must be written down — and the
documentation must not silently drift from the constants the shell actually
returns. This test ties the author-facing doc to the real exit codes: change a
code without updating the doc, and it fails.
"""

from conftest import REPO_ROOT
from lexiqr.cli import (
    EXIT_CLI_ERROR,
    EXIT_INVALID_LEXICON,
    EXIT_NO_MATCH,
    EXIT_OK,
)

DOC = REPO_ROOT / "docs" / "lexicon-authoring.md"
USAGE_EXIT_CODE = 2  # argparse's own conventional code


def test_the_authoring_doc_documents_every_exit_code() -> None:
    text = DOC.read_text(encoding="utf-8")

    for code in (
        EXIT_OK,
        EXIT_INVALID_LEXICON,
        USAGE_EXIT_CODE,
        EXIT_CLI_ERROR,
        EXIT_NO_MATCH,
    ):
        assert f"`{code}`" in text, f"exit code {code} is not documented"


def test_the_documented_contract_covers_both_commands_and_the_distinctions() -> None:
    text = DOC.read_text(encoding="utf-8").lower()

    assert "exit code" in text
    assert "validate" in text
    assert "try" in text
    assert "no match" in text  # the try distinction that matters most
    assert "usage" in text
