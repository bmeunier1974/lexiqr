"""The release checklist is present and covers the steps CI cannot.

A solo maintainer releasing unattended relies on this document for exactly the
steps a machine does not enforce — the recipe review, the one-time
trusted-publisher setup. This guards that those items stay written down and the
checklist stays discoverable from CONTRIBUTING.
"""

from conftest import REPO_ROOT

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


def test_it_lists_the_multi_tenant_recipe_review_as_a_manual_step() -> None:
    text = _releasing()

    assert "recipe" in text.lower()
    assert "[human]" in text  # called out as a human judgment, not a CI check


def test_it_documents_the_schema_republication_procedure() -> None:
    """Changing a published schema's bytes is a republication, not an edit.

    The test that enforces it only says *something drifted*; it cannot say which
    four things have to move together. Left undocumented, the next maintainer
    reconstructs the procedure from a failing assertion — so the steps, and the
    test that guards them, are written down here.
    """
    text = _releasing()

    assert "republication" in text.lower()
    assert "$id" in text
    assert "published.json" in text
    assert "sha256" in text.lower()
    assert "test_schema_publication.py" in text


def test_it_documents_the_pypi_registration_and_the_tag_push_steps() -> None:
    text = _releasing()

    assert "trusted publish" in text.lower() or "trusted publisher" in text.lower()
    assert "pending publisher" in text.lower()
    assert "git tag" in text and "git push origin" in text
