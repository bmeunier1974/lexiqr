"""What core accepts and rejects when a lexicon is loaded.

Validation happens at `EntityResolver` construction, never at `transform()`
time: an integrating developer's misconfiguration must surface at startup, not
in production traffic.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from lexiqr import EntityResolver, ValidationError

REPO_ROOT = Path(__file__).resolve().parent.parent
FLOOFF = REPO_ROOT / "examples" / "flooff.lexicon.json"


def flooff_document() -> Any:
    return json.loads(FLOOFF.read_text(encoding="utf-8"))


def test_a_lexicon_declaring_an_unsupported_schema_version_is_rejected() -> None:
    document = flooff_document()
    document["schemaVersion"] = "99"

    with pytest.raises(ValidationError) as raised:
        EntityResolver.from_dict(document)

    message = str(raised.value)
    assert "99" in message
    assert "1" in message


def test_a_lexicon_with_no_schema_version_at_all_is_rejected_the_same_way() -> None:
    document = flooff_document()
    del document["schemaVersion"]

    with pytest.raises(ValidationError):
        EntityResolver.from_dict(document)


def test_the_version_check_precedes_any_other_reading_of_the_document() -> None:
    """A document core cannot interpret is reported as such, not as a crash.

    Core has no idea what a future format's entities look like, so it must not
    try to read them before deciding it understands the version at all.
    """
    unreadable = {"schemaVersion": "99", "entities": "not what v1 means by this"}

    with pytest.raises(ValidationError) as raised:
        EntityResolver.from_dict(unreadable)

    assert raised.value.field == "schemaVersion"


def test_a_lexicon_file_is_validated_when_the_resolver_is_built(
    tmp_path: Path,
) -> None:
    document = flooff_document()
    document["schemaVersion"] = "99"
    path = tmp_path / "future.lexicon.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValidationError):
        EntityResolver.from_file(path)


def test_no_invalid_lexicon_survives_construction_to_reach_transform() -> None:
    """Misconfiguration surfaces at startup, never in production traffic."""
    document = flooff_document()
    document["schemaVersion"] = "99"

    try:
        resolver = EntityResolver.from_dict(document)
    except ValidationError:
        return

    pytest.fail(
        "construction accepted an invalid lexicon; "
        f"the failure would have been deferred to transform(): "
        f"{resolver.transform('wo ist flooff', 'de-DE')}"
    )
