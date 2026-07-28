"""The sample run, executed — the transcript the README points a reader at.

`examples/demo.py` is the one command that resolves a realistic tenant lexicon
and prints what lexiqr produced, section by section, asserting each claim as it
goes. It is a gate as well as a transcript: a false claim exits non-zero.

So this file asserts three things of decreasing breadth, because each catches
what the others cannot:

- the run exits zero and its output equals the committed golden after per-line
  normalization — which catches a wording change anywhere in it;
- a handful of the facts it prints are asserted by name, so that a golden
  regenerated from a *broken* run still fails here;
- the transcript carries a section for every section the run declares, so that
  a deleted section cannot quietly drop a claim.

Prior art for all three is `test_readme_quickstart.py`, which runs the extracted
blocks, normalizes before comparing, and then re-asserts the founding story's
two facts by name on top of the comparison.

The run's import-safety is asserted here too, by observation rather than in
prose: importing the module must print nothing. That is what makes the unit
tests over its render helper possible, and it is what keeps the golden honest —
an import-time side effect would be output nobody declared.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import demo
import pytest

from conftest import REPO_ROOT
from lexiqr import Lexicon, ValidationError

EXAMPLES = REPO_ROOT / "examples"
RUN = EXAMPLES / "demo.py"
GOLDEN = EXAMPLES / "demo.golden.txt"
LEXICON = EXAMPLES / "medien.lexicon.json"

#: How the golden is rebuilt after an intended change to the transcript. Named
#: here as well as in the run's own docstring, because this is where a
#: maintainer meets the failure that sends them looking for it.
REGENERATE = "uv run python examples/demo.py > examples/demo.golden.txt"


def normalize(text: str) -> str:
    """Compare by content, not by trailing spaces or edge blank lines.

    A platform's newline convention is not a failure; a wording change is.
    """
    return "\n".join(line.rstrip() for line in text.strip("\n").splitlines()).strip()


def collapsed(text: str) -> str:
    """`text` with its wrapping undone, so a sentence broken across lines is findable.

    The transcript wraps to a fixed width, which puts a line break in the middle
    of every long value it prints. A test that wants to find a whole sentence in
    it either has to know where the run wrapped — which is testing the
    formatter — or flatten the whitespace first. This is the second.
    """
    return " ".join(text.split())


def transcript_of(section_name: str) -> str:
    """Just the lines the named section printed, collapsed onto one line.

    A by-name assertion has to look inside the section that makes the claim, not
    across the whole transcript: `de-DE` appears in half the sections, so
    "the rejection names the locale" would pass on a run that stopped printing
    it. The section is found by asking the run which position it declares it in,
    so renumbering the transcript cannot silently point this at the wrong text.
    """
    numbered = [
        number
        for number, section in enumerate(demo.SECTIONS, start=1)
        if section.__name__ == section_name
    ]
    assert numbered, f"the run declares no section named {section_name!r}"

    golden = GOLDEN.read_text(encoding="utf-8")
    marker = f"--- {numbered[0]}. "
    assert marker in golden, f"{GOLDEN.name} has no section {numbered[0]}: {REGENERATE}"
    return collapsed(golden.split(marker, 1)[1].split("\n--- ", 1)[0])


def run(cwd: Path) -> subprocess.CompletedProcess[str]:
    """The sample run, as a reader would invoke it, from `cwd`."""
    return subprocess.run(
        [sys.executable, str(RUN)],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_the_run_exits_zero_and_prints_the_committed_golden() -> None:
    """The broad assertion: every rendered character, pinned.

    A change in wording anywhere in the transcript fails here, which is the
    trade this golden exists to make — the README quotes this output, so text
    that can drift silently is text the front page can lie about.
    """
    result = run(cwd=REPO_ROOT)

    assert result.returncode == 0, result.stdout + result.stderr
    assert normalize(result.stdout) == normalize(GOLDEN.read_text(encoding="utf-8")), (
        f"the sample run's output no longer matches {GOLDEN.name}. If the change "
        f"was intended, regenerate it: {REGENERATE}"
    )


def test_importing_the_run_prints_nothing() -> None:
    """Import-safety, observed rather than promised in prose.

    Two things rest on it. The unit tests over the render helper import this
    module, which a module that resolved a lexicon or reconfigured a stream at
    import time would make expensive and order-dependent. And the golden would
    stop being trustworthy: an import-time side effect is output no section
    declared and no claim covers.
    """
    result = subprocess.run(
        [sys.executable, "-c", "import demo"],
        cwd=EXAMPLES,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "", f"importing the run printed: {result.stdout!r}"
    assert result.stderr == "", f"importing the run wrote to stderr: {result.stderr!r}"


def imported_by(source: str) -> set[str]:
    """The top-level modules `source` imports, however it spells the import."""
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module.split(".")[0])
    return modules


def test_the_run_imports_nothing_but_lexiqr_and_the_standard_library() -> None:
    """What makes the run pointable at an installed wheel.

    The release workflow runs it in a clean virtualenv holding lexiqr and
    nothing else, and a reader is invited to copy a section into their own
    service. A dev-only import would break the first and mislead the second.
    """
    modules = imported_by(RUN.read_text(encoding="utf-8"))

    assert "lexiqr" in modules, "a sample run that never imports lexiqr proves nothing"
    outside = modules - {"lexiqr", "__future__"} - set(sys.stdlib_module_names)
    assert not outside, f"the run reaches outside lexiqr and the stdlib: {outside}"


def test_the_run_prints_the_same_transcript_from_any_working_directory(
    tmp_path: Path,
) -> None:
    """A reader who runs it from elsewhere must not meet a failure about paths.

    The run finds its lexicon relative to its own file, and names it in the
    transcript by that relative spelling rather than by the absolute path it
    resolved — so neither the exit code nor a single rendered character depends
    on where the command was typed.
    """
    from_elsewhere = run(cwd=tmp_path)

    assert from_elsewhere.returncode == 0, from_elsewhere.stdout + from_elsewhere.stderr
    assert normalize(from_elsewhere.stdout) == normalize(run(cwd=REPO_ROOT).stdout)
    assert str(REPO_ROOT) not in from_elsewhere.stdout, (
        "the transcript names an absolute path, so it would differ on every machine"
    )


#: The run with one extra section that cannot hold. Written as a program rather
#: than patched in-process because the thing under test is the whole gate — the
#: driver catching the assertion, the message it prints, and the exit code a CI
#: step or a release job actually reads.
A_BROKEN_SECTION = '''
import sys

import demo


def a_claim_this_run_cannot_make() -> None:
    """A section deliberately broken, to watch the driver catch it [C0]"""
    raise AssertionError("the printed result did not match the claim")


demo.SECTIONS = (*demo.SECTIONS, a_claim_this_run_cannot_make)
sys.exit(demo.main())
'''


def test_the_driver_names_the_failing_section_and_exits_non_zero() -> None:
    """What makes the run a gate rather than a brochure.

    Every section asserts, but an assertion nobody acts on is decoration. The
    driver is the mechanism that turns a false claim into a red build, so it is
    watched here doing exactly that: a section that cannot hold is caught, named
    by number *and* by function name so a maintainer knows which claim broke
    without bisecting the transcript, and the run refuses to close with `OK`.
    """
    result = subprocess.run(
        [sys.executable, "-c", A_BROKEN_SECTION],
        cwd=EXAMPLES,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    failing = len(demo.SECTIONS) + 1
    assert result.returncode != 0, result.stdout
    assert f"FAIL in section {failing} (a_claim_this_run_cannot_make)" in result.stdout
    assert "the printed result did not match the claim" in result.stdout
    assert demo.CLOSING not in result.stdout, (
        "the run closed by claiming every section held, having just watched one fail"
    )


def test_the_transcript_carries_every_section_the_run_declares() -> None:
    """A deleted section must not be able to quietly drop a claim.

    The golden comparison alone cannot see this: delete a section, regenerate,
    and the two agree again. So the transcript is checked against the run's own
    declared list of sections instead — which is also why the run is import-safe,
    since reading `SECTIONS` costs an import and nothing else.
    """
    golden = GOLDEN.read_text(encoding="utf-8")

    assert demo.SECTIONS, "a sample run with no sections demonstrates nothing"
    for number, section in enumerate(demo.SECTIONS, start=1):
        assert f"--- {number}. {demo.title_of(section)} ---" in golden, (
            f"section {number} ({section.__name__}) is declared by the run but is "
            f"not in {GOLDEN.name}. Regenerate it: {REGENERATE}"
        )


def test_the_transcript_names_what_the_lexicon_declares() -> None:
    """The narrow assertion, and the reason the golden is not the whole test.

    Everything here is derived from the lexicon *document*, not from the run —
    so it still fails if the run were to drop an entry, lose a locale, or stop
    reading the shared entity, and the golden were then regenerated from that
    broken state. A golden can only ever say "unchanged"; this says "correct".
    """
    document = json.loads(LEXICON.read_text(encoding="utf-8"))
    declared = document["entities"]
    entries = sorted(declared)
    entities = sorted(
        {entry.get("canonicalId", entry_id) for entry_id, entry in declared.items()}
    )
    locales = sorted(
        {locale for entry in declared.values() for locale in entry["locales"]}
    )

    golden = GOLDEN.read_text(encoding="utf-8")

    assert len(entities) < len(entries), (
        "the example lexicon has stopped resolving several entries to one entity, "
        "which is the thing this sample run exists to show"
    )
    assert ", ".join(entries) in golden, f"the transcript does not name {entries}"
    assert ", ".join(entities) in golden, f"the transcript does not name {entities}"
    assert ", ".join(locales) in golden, f"the transcript does not name {locales}"
    assert document["defaultLocale"] in golden


def test_the_transcript_names_the_coordinates_the_loader_really_reports() -> None:
    """The rejection section, pinned to the loader rather than to the rendering.

    The invalid document is taken from the run and handed to the loader here, so
    the coordinates compared against the transcript are the ones core produces
    today. If core stopped naming the locale, or renamed the field, a golden
    regenerated from that state would agree with itself and this would not.
    """
    with pytest.raises(ValidationError) as refused:
        Lexicon.from_dict(demo.A_LEXICON_WITH_A_MISTAKE)

    rejected = refused.value
    printed = transcript_of("a_rejected_lexicon_names_the_entry_locale_and_field")

    for coordinate in (rejected.canonical_id, rejected.locale, rejected.field):
        assert coordinate is not None, f"the refusal has no coordinates: {rejected}"
        assert coordinate in printed, f"the section does not name {coordinate!r}"
    assert collapsed(str(rejected)) in printed, (
        f"the section does not carry the message the loader raised: {rejected}"
    )


def test_the_run_records_how_its_golden_is_regenerated() -> None:
    """A golden nobody knows how to rebuild is a golden that gets hand-edited.

    Hand-editing is the one thing that makes it worthless: the file would stop
    being a record of what the command printed and become a record of what
    somebody wished it printed. So the command is written down where the person
    holding the failure will look — beside the code that produces it — the way
    `scripts/report_equality.py` documents its own `--write`.
    """
    assert REGENERATE in RUN.read_text(encoding="utf-8"), (
        f"{RUN.name} does not record the command that rebuilds {GOLDEN.name}: "
        f"{REGENERATE}"
    )
