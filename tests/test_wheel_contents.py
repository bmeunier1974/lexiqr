"""What the built wheel must contain, checked at build time — not after publish.

The PyPI page is the project's front door for anyone who never opens GitHub, and
the wheel is what they install. A packaging gap — the schema left behind, the
type marker dropped, the console script undeclared — is the kind of thing that
looks fine locally and is only discovered once it is published and someone's
`pip install` is missing a piece. So the built artifact is inspected here: build
the wheel, open it, and assert it carries what an integrating developer needs.

The artifact itself comes from the session-scoped `wheel` fixture in conftest,
so the build happens once for the whole run rather than once per file that
inspects it.
"""

import email
import email.message
import re
import zipfile
from pathlib import Path


def test_the_wheel_bundles_the_versioned_json_schema(wheel: Path) -> None:
    """The lexicon format ships alongside the code, so an integrating developer
    has the contract their tenants' files must meet without visiting GitHub."""
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()

    schema_files = [n for n in names if n.endswith("lexicon.v1.schema.json")]
    assert schema_files, names


def test_the_wheel_bundles_the_type_information_marker(wheel: Path) -> None:
    """Without py.typed in the artifact, a consumer's checker treats the whole
    package as Any — everything looks typed until it is installed."""
    with zipfile.ZipFile(wheel) as archive:
        assert "lexiqr/py.typed" in archive.namelist()


def test_the_wheel_declares_the_lexiqr_console_entry_point(wheel: Path) -> None:
    """So the CLI is on PATH after install, with no separate step."""
    entry_points = _read_metadata_member(wheel, "entry_points.txt")

    assert "[console_scripts]" in entry_points
    assert "lexiqr = lexiqr.cli:main" in entry_points


def test_the_only_runtime_dependency_is_rapidfuzz(wheel: Path) -> None:
    """Adding lexiqr must not drag a dependency tree into a service."""
    metadata = _parse_metadata(wheel)
    requires = metadata.get_all("Requires-Dist") or []

    matches = [re.match(r"[A-Za-z0-9._-]+", req) for req in requires]
    names = [m.group() for m in matches if m is not None]
    assert names == ["rapidfuzz"], requires


def test_the_wheel_is_pure_python_so_no_compiler_is_needed(wheel: Path) -> None:
    """A py3-none-any wheel installs without a build toolchain; rapidfuzz ships
    its own prebuilt wheels, so nothing in the tree needs a compiler either."""
    assert wheel.name.endswith("-py3-none-any.whl"), wheel.name


def test_the_metadata_is_release_quality(wheel: Path) -> None:
    """The PyPI page is the front door: a summary, the README as the long
    description, the license, links home and to the issue tracker, the Python
    versions, and classifiers must all be present."""
    metadata = _parse_metadata(wheel)

    assert metadata.get("Summary")
    assert metadata.get("Description-Content-Type") == "text/markdown"
    assert metadata.get_payload(), "the README ships as the long description"
    # PEP 639: the SPDX expression is the modern spelling; the legacy `License`
    # field and `License ::` classifier remain acceptable so this test states
    # "the license is in the metadata", not which metadata version carries it.
    assert (
        metadata.get("License-Expression")
        or metadata.get("License")
        or any(
            c.startswith("License ::") for c in (metadata.get_all("Classifier") or [])
        )
    )
    assert metadata.get_all("License-File"), "the license text ships in the wheel"
    assert metadata.get("Requires-Python")

    project_urls = metadata.get_all("Project-URL") or []
    joined = " ".join(project_urls).lower()
    assert "repository" in joined or "homepage" in joined, project_urls
    assert "issue" in joined or "tracker" in joined or "bug" in joined, project_urls

    classifiers = metadata.get_all("Classifier") or []
    assert any("Programming Language :: Python :: 3.10" in c for c in classifiers)


def _read_metadata_member(wheel: Path, member: str) -> str:
    with zipfile.ZipFile(wheel) as archive:
        name = next(n for n in archive.namelist() if n.endswith(f".dist-info/{member}"))
        return archive.read(name).decode("utf-8")


def _parse_metadata(wheel: Path) -> email.message.Message:
    return email.message_from_string(_read_metadata_member(wheel, "METADATA"))
