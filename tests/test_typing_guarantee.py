"""The typing guarantee (C10), proven from the consumer's side.

That lexiqr type-checks itself proves nothing about what an integrating
developer gets. The promise is that adding lexiqr to a strictly-typed codebase
introduces no type errors and no `Any` leaks — so these tests build the wheel,
install it into a throwaway project, and type-check *that*.

They are slower than the rest of the suite on purpose: this is the only place
the guarantee is checked the way a user experiences it.
"""

import subprocess
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The distribution a consumer would actually install."""
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


def test_the_marker_that_makes_the_types_visible_ships_in_the_wheel(
    wheel: Path,
) -> None:
    """A py.typed present in the source tree but missing from the artifact is
    the classic silent failure: everything looks typed until it is installed,
    at which point the consumer's checker treats the whole package as Any."""
    with zipfile.ZipFile(wheel) as archive:
        assert "lexiqr/py.typed" in archive.namelist()


CONSUMER = '''\
"""A strictly-typed application that happens to depend on lexiqr.

It exercises the whole public surface the way a service would: build a
resolver from a tenant's file or from a dict pulled out of a database, run a
prompt through it, read the report, and handle a bad lexicon.
"""

from pathlib import Path

from lexiqr import EntityMatch, EntityResolver, MatchReport, ScoreTier, ValidationError


def resolver_for_tenant(lexicon_path: Path) -> EntityResolver:
    return EntityResolver.from_file(lexicon_path)


def resolver_from_database_row(document: dict[str, object]) -> EntityResolver | None:
    try:
        return EntityResolver.from_dict(document)
    except ValidationError as invalid:
        report_to_lexicon_owner(invalid.canonical_id, invalid.locale, invalid.field)
        return None


def report_to_lexicon_owner(
    canonical_id: str | None, locale: str | None, field: str | None
) -> None:
    print(f"lexicon problem at {canonical_id!r}/{locale!r}/{field!r}")


def canonical_ids(report: MatchReport) -> list[str]:
    return [match.canonical_id for match in report.matches]


def describe(match: EntityMatch) -> str:
    start, end = match.span
    tier: ScoreTier | None = match.score_tier
    correction: str | None = match.correction
    return (
        f"{match.surface_form}[{start}:{end}] -> "
        f"{match.canonical_id} ({tier}, {correction})"
    )


def main(lexicon_path: Path, prompt: str, locale: str) -> None:
    resolver: EntityResolver = resolver_for_tenant(lexicon_path)
    report: MatchReport = resolver.transform(prompt, locale)
    print(report.prompt, report.locale, canonical_ids(report))
    for match in report.matches:
        print(describe(match))
'''

MISUSE = """\
from pathlib import Path

from lexiqr import EntityResolver


def wrong_argument_types(resolver: EntityResolver) -> None:
    resolver.transform(42, "de-DE")


def field_that_does_not_exist(resolver: EntityResolver) -> None:
    print(resolver.transform("wo ist flooff", "de-DE").entities)


def wrong_return_type(path: Path) -> str:
    return EntityResolver.from_file(path)
"""


@pytest.fixture(scope="module")
def consumer_project(
    wheel: Path, tmp_path_factory: pytest.TempPathFactory
) -> tuple[Path, Path]:
    """A throwaway project with lexiqr installed from the wheel, and its own mypy."""
    project = tmp_path_factory.mktemp("consumer")
    (project / "app.py").write_text(CONSUMER, encoding="utf-8")
    (project / "misuse.py").write_text(MISUSE, encoding="utf-8")

    venv = project / ".venv"
    subprocess.run(["uv", "venv", str(venv)], check=True, capture_output=True)
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(venv / "bin" / "python"),
            str(wheel),
            "mypy",
        ],
        check=True,
        capture_output=True,
    )
    return project, venv / "bin" / "mypy"


def check(project: Path, mypy: Path, target: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(mypy), "--strict", "--no-incremental", target],
        cwd=project,
        capture_output=True,
        text=True,
    )


def test_a_strictly_typed_consumer_of_the_installed_wheel_checks_clean(
    consumer_project: tuple[Path, Path],
) -> None:
    project, mypy = consumer_project

    result = check(project, mypy, "app.py")

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("line", "misuse"),
    [
        (7, "passing an int where transform() wants a prompt"),
        (11, "reading a field the match report does not have"),
        (15, "returning a resolver where the signature promises a str"),
    ],
)
def test_the_consumers_type_checker_catches_misuse_of_the_api(
    consumer_project: tuple[Path, Path], line: int, misuse: str
) -> None:
    """The negative half, and the half that matters.

    A package whose public API resolves to `Any` also type-checks clean — it
    just checks nothing. Catching deliberate misuse is what proves the types
    reached the consumer intact.
    """
    project, mypy = consumer_project

    result = check(project, mypy, "misuse.py")

    assert result.returncode != 0
    assert f"misuse.py:{line}: error:" in result.stdout, f"{misuse}\n{result.stdout}"


REVEAL = """\
from pathlib import Path

from lexiqr import EntityResolver


def inspect(path: Path) -> None:
    resolver = EntityResolver.from_file(path)
    reveal_type(resolver)
    report = resolver.transform("wo ist flooff", "de-DE")
    reveal_type(report)
    reveal_type(report.prompt)
    reveal_type(report.matches)
    for match in report.matches:
        reveal_type(match.canonical_id)
        reveal_type(match.span)
        reveal_type(match.score_tier)
"""


@pytest.mark.parametrize(
    "revealed",
    [
        "lexiqr.resolver.EntityResolver",
        "lexiqr.types.MatchReport",
        "str",
        "tuple[lexiqr.types.EntityMatch, ...]",
        "tuple[int, int]",
        "lexiqr.types.ScoreTier",
    ],
)
def test_nothing_a_consumer_touches_resolves_to_any(
    consumer_project: tuple[Path, Path], revealed: str
) -> None:
    """A package that leaks `Any` type-checks clean by checking nothing.

    So ask the consumer's own checker what it sees, and require concrete
    types all the way down — including inside the match report's tuples,
    where an untyped container would hide the leak.
    """
    project, mypy = consumer_project
    (project / "reveal.py").write_text(REVEAL, encoding="utf-8")

    result = check(project, mypy, "reveal.py")

    assert f'Revealed type is "{revealed}"' in result.stdout, result.stdout
    assert "Any" not in result.stdout
