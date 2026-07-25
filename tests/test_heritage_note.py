"""The heritage note is discoverable and states the clean-room position.

Provenance is not something CI can prove — whether the reimplementation really
was clean-room is a human judgment recorded in HERITAGE.md and confirmed on the
release checklist, deliberately not gated here. What CI *can* keep true is that
the note exists, sits beside the license, still makes the claims it is supposed
to make, and stays discoverable from the README. This is a drift guard on those
facts, not an assertion that the provenance question is settled.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HERITAGE = REPO_ROOT / "HERITAGE.md"
LICENSE = REPO_ROOT / "LICENSE"
README = REPO_ROOT / "README.md"


def test_the_heritage_note_and_the_license_both_ship() -> None:
    """The note says where the code came from; the license says how it may be
    used. Anyone evaluating lexiqr should find both, side by side."""
    assert HERITAGE.is_file()
    assert LICENSE.is_file()


def test_the_note_states_the_clean_room_position() -> None:
    text = HERITAGE.read_text(encoding="utf-8").lower()

    assert "clean-room" in text
    assert "735" in text
    assert "no branch-735 source" in text  # the specific claim, not a vague gesture
    assert "behavioral spec" in text or "behavioral specification" in text


def test_the_note_records_its_status_as_a_release_prerequisite() -> None:
    """The note must carry, in its own text, that it gates the 1.0.0 tag and
    that this is a checklist item rather than a CI gate."""
    text = HERITAGE.read_text(encoding="utf-8").lower()

    assert "1.0.0" in text
    assert "prerequisite" in text
    assert "checklist" in text and "ci" in text


def test_the_readme_points_to_the_heritage_note() -> None:
    assert "HERITAGE.md" in README.read_text(encoding="utf-8")
