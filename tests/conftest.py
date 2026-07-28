"""The suite's fixture seam: one home for what a test needs to know about a lexicon.

Three jobs, and the last one is why this file is worth reading before writing a
test.

First, `scripts/` is not a package — the release workflow runs each file as a
plain script — but the release-consistency gate is a *pure* module whose whole
point is being unit-testable against crafted inputs rather than only observable
by pushing real tags. Putting the scripts directory on the path lets a test
import that checker directly, without the subprocess indirection the I/O-bound
scripts (reproduce_flooff, report_equality) are exercised through. `examples/` is
on the path for the same reason and no other: the sample run is import-safe by
design, so a test can import it and exercise its render helper directly instead
of reading lines back out of a subprocess's transcript.

Second, the two paths every test file used to rediscover for itself — the repo
root and the flooff example lexicon — are named here once, so a directory move
is one edit rather than thirty.

Third, and the substantial one: the lexicon format is knowledge, and knowledge
copied into forty test files drifts. `lexicon_document` is the one place a test
gets a lexicon from, and the only place the `schemaVersion` a fixture declares
is written. Authoring a new test starts here.

The deliberate exception is a test whose subject *is* the document — what core
does with an unsupported `schemaVersion`, with the field missing entirely, with
a file that is not JSON at all. Those keep their documents inline and literal,
where a reader can see exactly what is being rejected. Concentrating the
format's knowledge is the goal; hiding it from the tests that assert on it is
not. `perf/lexicon_generator.py` is the same exception in another shape: the
benchmark lexicon it emits is itself the reviewable, byte-pinned fixture, so it
writes the format out in full and stays free of anything imported from here.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

#: The repo root. Every path the suite reaches for is spelled relative to this.
REPO_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "examples"))

#: The flooff scenario's published lexicon: "flooff" → `product`, in de-DE.
FLOOFF_LEXICON = REPO_ROOT / "examples" / "flooff.lexicon.json"

#: The lexicon format version core implements, and the one every built fixture
#: declares. A test that means a *different* version is asserting on the version
#: itself and writes it inline.
SCHEMA_VERSION = "1"

#: The locale the flooff scenario is authored in, and what a document declares
#: as its default when a test does not care.
DEFAULT_LOCALE = "de-DE"


def lexicon_document(
    locale: str = DEFAULT_LOCALE,
    *,
    default_locale: str | None = None,
    entities: Mapping[str, Mapping[str, Any]] | None = None,
    **named_entities: Mapping[str, Any],
) -> dict[str, Any]:
    """A lexicon document built from the parts a test actually has an opinion on.

    Each keyword argument names an entity by canonical ID and gives its surface
    forms in `locale` — the shape nearly every test wants::

        lexicon_document("en-GB", product={"preferred": {"singular": "widget"}})

    An entity that spans locales gives the entity object the format itself
    writes, and is passed through untouched::

        lexicon_document(invoice={"locales": {"de-DE": forms, "de-AT": forms}})

    `entities` takes that same mapping for canonical IDs that are computed
    rather than written, and `default_locale` overrides the declared default,
    which otherwise follows `locale`.
    """
    declared: dict[str, Mapping[str, Any]] = {**(entities or {}), **named_entities}
    return {
        "schemaVersion": SCHEMA_VERSION,
        "defaultLocale": locale if default_locale is None else default_locale,
        "entities": {
            canonical_id: (
                dict(entity)
                if "locales" in entity
                else {"locales": {locale: dict(entity)}}
            )
            for canonical_id, entity in declared.items()
        },
    }


def flooff_document() -> dict[str, Any]:
    """The published flooff lexicon, freshly parsed so a caller may edit its copy."""
    document = json.loads(FLOOFF_LEXICON.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


@pytest.fixture(scope="session")
def wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The distribution a consumer would actually install.

    Session-scoped because a wheel build is the most expensive thing the suite
    does and the artifact is identical for every test that inspects it: what it
    contains, and what a strictly-typed consumer sees after installing it.
    """
    out = tmp_path_factory.mktemp("dist")
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(out)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )
    built = list(out.glob("*.whl"))
    assert len(built) == 1, built
    return built[0]
