"""The ADR 0003 equivalence guarantee, as a CI-tested fact.

*A lexicon file that passes the published JSON Schema loads in core.* That is
what makes offline validation a trustworthy preflight for a lexicon author
rather than an approximation of one.

Two validators over one format can drift, so this harness runs every lexicon
document in the repository through both — a standard JSON Schema validator and
core's loader — and asserts they agree. The single licensed disagreement is
the documented semantic set (docs/lexicon-semantic-checks.md), where core is
deliberately stricter; anything else is drift, and fails here.

Fixtures are discovered, never listed: a document added to the corpus comes
under the guarantee without anyone remembering to edit this file.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as SchemaValidationError

from lexiqr import EntityResolver
from lexiqr import ValidationError as CoreValidationError

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "lexicon.v1.schema.json"
SEMANTIC_CORPUS = REPO_ROOT / "schema" / "fixtures" / "semantic"
DIVERGENCE_DOC = REPO_ROOT / "docs" / "lexicon-semantic-checks.md"

#: Every place in the repository that holds lexicon documents. Directories,
#: not files — the point is that adding a fixture needs no edit here.
CORPUS_ROOTS = (REPO_ROOT / "examples", REPO_ROOT / "schema" / "fixtures")


def corpus() -> list[Path]:
    return sorted(
        path for root in CORPUS_ROOTS for path in root.rglob("*.lexicon.json")
    )


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    return Draft202012Validator(load(SCHEMA_PATH))


def passes_schema(validator: Draft202012Validator, document: Any) -> bool:
    try:
        validator.validate(document)
    except SchemaValidationError:
        return False
    return True


def test_the_harness_discovers_the_whole_corpus() -> None:
    """Guards the harness itself: discovery that quietly stops finding files
    would turn every assertion below into a vacuous pass."""
    found = {relative(path) for path in corpus()}

    assert "examples/flooff.lexicon.json" in found
    assert any(path.startswith("schema/fixtures/valid/") for path in found)
    assert any(path.startswith("schema/fixtures/invalid/") for path in found)
    assert any(path.startswith("schema/fixtures/semantic/") for path in found)
    assert len(found) >= 14


@pytest.mark.parametrize("fixture", corpus(), ids=relative)
def test_a_document_that_passes_the_schema_loads_in_core(
    fixture: Path, validator: Draft202012Validator
) -> None:
    """The guarantee, in the direction ADR 0003 states it.

    The one licensed exception is the documented semantic set: those documents
    pass the schema and core is *deliberately* stricter about them.
    """
    document = load(fixture)
    if not passes_schema(validator, document):
        pytest.skip("the schema rejects this document; the guarantee says nothing")

    if fixture.parent == SEMANTIC_CORPUS:
        pytest.skip("a documented semantic divergence; asserted below")

    EntityResolver.from_dict(document)


@pytest.mark.parametrize(
    "fixture", sorted(SEMANTIC_CORPUS.glob("*.lexicon.json")), ids=relative
)
def test_every_documented_divergence_behaves_the_way_the_document_says(
    fixture: Path, validator: Draft202012Validator
) -> None:
    """The divergence list is a claim about behavior, not a wish.

    Each entry claims a document the schema accepts and core refuses. If core
    stopped refusing one, the list would be describing a check that no longer
    exists — misleading in the opposite direction, and just as bad.
    """
    document = load(fixture)

    validator.validate(document)

    with pytest.raises(CoreValidationError):
        EntityResolver.from_dict(document)

    assert fixture.name in DIVERGENCE_DOC.read_text(encoding="utf-8")


def test_the_second_validator_never_becomes_a_runtime_dependency() -> None:
    """The harness proves equivalence by using a *different* implementation.

    A jsonschema that leaked into `dependencies` would both weigh on every
    installation and tempt core into simply calling it — at which point the
    two validators are one, and the harness proves nothing.
    """
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    runtime = pyproject.split("dependencies = [", 1)[1].split("]", 1)[0]

    assert "rapidfuzz" in runtime
    assert "jsonschema" not in runtime
    assert "[dependency-groups]" in pyproject
    assert "jsonschema" in pyproject.split("[dependency-groups]", 1)[1]


@pytest.mark.parametrize("fixture", corpus(), ids=relative)
def test_core_rejects_a_schema_valid_document_only_where_it_is_documented(
    fixture: Path, validator: Draft202012Validator
) -> None:
    """The drift check — the reason this harness exists.

    If core grows a check the divergence document does not license, a lexicon
    author's offline validation silently stops predicting whether their file
    will load. That is exactly the failure ADR 0003 was written to prevent, so
    it must fail loudly here rather than surface as a support ticket.
    """
    document = load(fixture)
    if not passes_schema(validator, document):
        pytest.skip("the schema rejects this document; the guarantee says nothing")

    try:
        EntityResolver.from_dict(document)
    except CoreValidationError as rejected:
        assert fixture.parent == SEMANTIC_CORPUS, (
            f"{relative(fixture)} passes the published schema but core rejects it: "
            f"{rejected}\n"
            f"That is an undocumented divergence. Either fix core, or — if the "
            f"check is deliberate — move the fixture to {relative(SEMANTIC_CORPUS)} "
            f"and enumerate the check in {relative(DIVERGENCE_DOC)}."
        )
        assert fixture.name in DIVERGENCE_DOC.read_text(encoding="utf-8"), (
            f"{relative(fixture)} is a divergence that "
            f"{relative(DIVERGENCE_DOC)} does not name."
        )
