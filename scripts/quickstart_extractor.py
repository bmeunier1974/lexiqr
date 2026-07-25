"""Pull the runnable units out of a README, so the quickstart is the test.

The README's quickstart is lexiqr's front page and, by choice, its own test:
the code a reader copies is the code CI runs, so the two cannot drift. That
choice makes the README load-bearing, and this module is the one place that
fragility is concentrated. It takes markdown and returns the units meant to run,
each keyed so a test can run it the right way — Python as Python, shell as the
CLI — plus any inline file (the lexicon) the units point at.

Nothing is guessed. A fenced block runs only because a `<!-- quickstart:… -->`
directive on the line before it says so, which lets prose examples and
aspirational snippets sit in the same README as tested ones without the
extractor mistaking one for the other. The directives:

    <!-- quickstart:python -->     the next block is an executable Python unit
    <!-- quickstart:shell -->      the next block is an executable CLI command
    <!-- quickstart:expected -->   the next block is the expected output of the
                                   unit just before it
    <!-- quickstart:file PATH -->  the next block is written to PATH, so a unit
                                   can reference it (the inline lexicon)
    <!-- quickstart:skip -->       the next block is explicitly illustrative and
                                   collected as nothing (the multi-tenant recipe)

A README that marks nothing executable raises rather than returning an empty
collection: a quickstart that silently tests nothing is worse than one that
fails, because it reads as a guarantee while being none.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Kind = Literal["python", "shell"]

_DIRECTIVE = re.compile(
    r"^\s*<!--\s*quickstart:(?P<kind>\S+)(?:\s+(?P<arg>.*?))?\s*-->\s*$"
)
_FENCE = re.compile(r"^\s*```")


class QuickstartExtractionError(Exception):
    """The README's quickstart could not be turned into runnable units."""


@dataclass(frozen=True)
class RunnableUnit:
    """One thing to run, and what it should produce.

    `kind` says how to run it — Python source executed as Python, or a shell
    line invoked as the CLI. `expected_output`, when present, is what its stdout
    must equal: a unit that runs but resolves nothing would pass a smoke test,
    so the quickstart asserts output, not merely the absence of an exception.
    """

    kind: Kind
    code: str
    expected_output: str | None = None


@dataclass(frozen=True)
class MaterializedFile:
    """An inline block to write to disk so the runnable units can reference it."""

    path: str
    content: str


@dataclass(frozen=True)
class Quickstart:
    """Everything extracted from the README: the files to write, then the units."""

    units: list[RunnableUnit] = field(default_factory=list)
    files: list[MaterializedFile] = field(default_factory=list)


def extract_quickstart(markdown: str) -> Quickstart:
    """Turn README markdown into its runnable units and inline files."""
    units: list[RunnableUnit] = []
    files: list[MaterializedFile] = []

    lines = markdown.splitlines(keepends=True)
    i = 0
    pending: re.Match[str] | None = None
    while i < len(lines):
        directive = _DIRECTIVE.match(lines[i])
        if directive is not None:
            pending = directive
            i += 1
            continue
        if _FENCE.match(lines[i]) and pending is not None:
            body, i = _read_fenced_body(lines, i)
            _apply_directive(pending, body, units, files)
            pending = None
            continue
        i += 1

    if not units:
        raise QuickstartExtractionError(
            "no executable blocks found: the markdown marks nothing with a "
            "<!-- quickstart:python --> or <!-- quickstart:shell --> directive, "
            "so the quickstart would test nothing. Mark the blocks meant to run."
        )

    return Quickstart(units=units, files=files)


def _apply_directive(
    directive: re.Match[str],
    body: str,
    units: list[RunnableUnit],
    files: list[MaterializedFile],
) -> None:
    """Fold one directive+block into the units or files, by the directive's kind."""
    kind = directive.group("kind")

    if kind == "python":
        units.append(RunnableUnit(kind="python", code=body))
        return

    if kind == "shell":
        units.append(RunnableUnit(kind="shell", code=body))
        return

    if kind == "file":
        path = (directive.group("arg") or "").strip()
        if not path:
            raise QuickstartExtractionError(
                "a <!-- quickstart:file … --> directive needs a path: "
                "<!-- quickstart:file lexicon.json -->"
            )
        files.append(MaterializedFile(path=path, content=body))
        return

    if kind == "skip":
        # Explicitly illustrative: a block that says "do not run me", so
        # aspirational or partial snippets (the multi-tenant recipe) can be
        # marked non-executable rather than merely left unmarked, and cannot be
        # collected by accident.
        return

    if kind == "expected":
        if not units:
            raise QuickstartExtractionError(
                "an <!-- quickstart:expected --> block has no runnable unit "
                "before it to attach to; expected output describes the unit it "
                "follows."
            )
        units[-1] = RunnableUnit(
            kind=units[-1].kind, code=units[-1].code, expected_output=body
        )
        return

    raise QuickstartExtractionError(f"unknown quickstart directive: {kind!r}")


def materialize_files(quickstart: Quickstart, root: Path) -> None:
    """Write each inline file under `root`, so the units can reference it.

    What a reader copies is exactly what CI ran: the lexicon lives in the README
    block, not in a fixture file the block could drift from, and this writes that
    block to disk for the runnable units that point at it.
    """
    for file in quickstart.files:
        target = root / file.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(file.content, encoding="utf-8")


def _read_fenced_body(lines: list[str], fence_start: int) -> tuple[str, int]:
    """The text between an opening fence at `fence_start` and its close.

    Returns the joined body and the index just past the closing fence.
    """
    body: list[str] = []
    j = fence_start + 1
    while j < len(lines) and not _FENCE.match(lines[j]):
        body.append(lines[j])
        j += 1
    return "".join(body), j + 1
