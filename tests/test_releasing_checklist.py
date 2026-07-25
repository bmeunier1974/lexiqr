"""The release checklist is present and covers the steps CI cannot.

A solo maintainer releasing unattended relies on this document for exactly the
steps a machine does not enforce — the heritage prerequisite, the recipe review,
the one-time trusted-publisher setup. This guards that those items stay written
down and the checklist stays discoverable from CONTRIBUTING.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RELEASING = REPO_ROOT / "RELEASING.md"
CONTRIBUTING = REPO_ROOT / "CONTRIBUTING.md"


def _releasing() -> str:
    return RELEASING.read_text(encoding="utf-8")


def test_the_checklist_exists_and_is_linked_from_contributing() -> None:
    assert RELEASING.is_file()
    assert "RELEASING.md" in CONTRIBUTING.read_text(encoding="utf-8")


def test_it_states_the_semver_and_changelog_rules_and_names_the_gate() -> None:
    text = _releasing()

    assert "emver" in text  # Semver / semver
    assert "CHANGELOG.md" in text
    assert "release_consistency.py" in text  # points at the enforcing gate


def test_it_lists_the_heritage_note_as_a_hard_prerequisite_of_1_0_0() -> None:
    text = _releasing()

    assert "HERITAGE.md" in text
    assert "1.0.0" in text
    assert "prerequisite" in text.lower()


def test_it_lists_the_multi_tenant_recipe_review_as_a_manual_step() -> None:
    text = _releasing()

    assert "recipe" in text.lower()
    assert "[human]" in text  # called out as a human judgment, not a CI check


def test_it_documents_the_pypi_registration_and_the_tag_push_steps() -> None:
    text = _releasing()

    assert "trusted publish" in text.lower() or "trusted publisher" in text.lower()
    assert "pending publisher" in text.lower()
    assert "git tag" in text and "git push origin" in text
