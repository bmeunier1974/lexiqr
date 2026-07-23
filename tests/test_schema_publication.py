"""The published schema, as a lexicon author consumes it.

An author validates offline with standard tooling and never installs lexiqr,
so the schema's `$id` is their contract: it must be a versioned URL that keeps
resolving to the same bytes forever. Nothing enforces that at runtime — no
server, no registry — so it is enforced here.
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "lexicon.v1.schema.json"
PUBLICATION = REPO_ROOT / "schema" / "published.json"
AUTHORING_DOC = REPO_ROOT / "docs" / "lexicon-authoring.md"
EXAMPLES = REPO_ROOT / "examples"

#: The `$id` scheme: this repository's raw content, at an immutable tag.
ID_URL = re.compile(
    r"https://raw\.githubusercontent\.com/bmeunier1974/lexiqr/"
    r"(?P<tag>v\d+\.\d+\.\d+)/schema/(?P<file>[\w.]+\.schema\.json)"
)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def package_version() -> str:
    line = next(
        line
        for line in (REPO_ROOT / "pyproject.toml")
        .read_text(encoding="utf-8")
        .split("\n")
        if line.startswith("version = ")
    )
    return line.split('"')[1]


def test_the_schema_id_is_an_immutable_versioned_url() -> None:
    """A `$id` at a branch or at `main` would change under an author's feet;
    a tagged path cannot, because the tag names a commit."""
    schema_id = load(SCHEMA_PATH)["$id"]

    matched = ID_URL.fullmatch(schema_id)

    assert matched, schema_id
    assert matched.group("file") == SCHEMA_PATH.name


def test_the_schema_still_holds_the_bytes_its_id_promises() -> None:
    """The reconciliation the publication record exists to force.

    `$id` claims a tag, and that tag resolves to fixed bytes on GitHub. Edit
    the schema and leave `$id` alone and the claim becomes a lie — an author's
    offline validation would then check a different schema from the one their
    file says it conforms to. Republishing means a new tag *and* a new `$id`;
    this test is what makes forgetting either one impossible.
    """
    record = load(PUBLICATION)[SCHEMA_PATH.name]
    digest = hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest()

    assert digest == record["sha256"], (
        f"{SCHEMA_PATH.name} has changed since it was published at "
        f"{record['publishedAt']}. A published schema version is immutable: "
        f"publish the new bytes at a new tag, point `$id` at it, and update "
        f"{PUBLICATION.name}."
    )


def test_the_id_and_the_publication_record_name_the_same_tag() -> None:
    schema_id = load(SCHEMA_PATH)["$id"]
    record = load(PUBLICATION)[SCHEMA_PATH.name]

    matched = ID_URL.fullmatch(schema_id)
    assert matched

    assert matched.group("tag") == record["publishedAt"]


def test_the_publication_tag_is_one_the_project_has_actually_reached() -> None:
    """An `$id` at a tag ahead of the package version resolves to nothing.

    A version bump does not move `$id` — that is immutability working, and the
    hash check above is what proves the schema really is unchanged. What is
    never allowed is claiming publication at a tag that does not exist yet.
    """
    record = load(PUBLICATION)[SCHEMA_PATH.name]

    published = tuple(
        int(part) for part in record["publishedAt"].lstrip("v").split(".")
    )
    current = tuple(int(part) for part in package_version().split("."))

    assert published <= current, (
        f"the schema claims publication at {record['publishedAt']}, but the "
        f"package is only at {package_version()}; that tag does not exist yet."
    )


@pytest.mark.parametrize(
    "example", sorted(EXAMPLES.glob("*.lexicon.json")), ids=lambda p: p.name
)
def test_every_example_lexicon_demonstrates_the_schema_reference(example: Path) -> None:
    """The docs tell authors to add `$schema`; the examples must show it.

    An example without it teaches the opposite of what the page says, and the
    example is what people copy.
    """
    document = load(example)

    assert document.get("$schema") == load(SCHEMA_PATH)["$id"]


def test_the_authoring_guide_tells_an_author_what_they_need() -> None:
    """The audience never installs lexiqr and never writes Python, so the
    page has to carry the whole story: the URL, how to check a file with
    standard tooling, how to wire an editor, and the one caveat."""
    guide = AUTHORING_DOC.read_text(encoding="utf-8")
    schema_id = load(SCHEMA_PATH)["$id"]

    assert schema_id in guide, "the exact `$id` URL to validate against"
    assert "$schema" in guide, "how to wire editor completion"
    assert "check-jsonschema" in guide or "jsonschema" in guide, "an offline tool"
    assert "docs/lexicon-semantic-checks.md" in guide or "semantic" in guide, (
        "the checks core enforces beyond the schema"
    )
