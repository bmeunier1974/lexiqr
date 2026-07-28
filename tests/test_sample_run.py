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
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import demo
import pytest

from conftest import REPO_ROOT
from lexiqr import (
    EntityMatch,
    EntityResolver,
    Lexicon,
    Metadata,
    ScoreTier,
    ValidationError,
)

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


def test_the_transcript_shows_the_exact_match_the_resolver_produces() -> None:
    """Section 3's line, pinned to the resolver rather than to the golden.

    The same prompt is resolved here, so if the span moved or the tier changed,
    a golden regenerated from that state would agree with itself and this would
    not. The slice assertion is the section's actual claim, and is made without
    going through the run's renderer at all.
    """
    match = (
        EntityResolver.from_file(LEXICON)
        .transform("wo ist die rechnung", "de-DE")
        .matches[0]
    )
    printed = transcript_of("an_exact_match_reports_entity_form_span_and_tier")
    start, end = match.span

    assert collapsed(demo.render_match(match)) in printed, (
        f"the section does not show the match the resolver returns: {match}"
    )
    assert f'prompt[{start}:{end}] == "{match.surface_form}"' in printed, (
        "the section does not show the original prompt sliced by the span"
    )


def test_the_transcript_shows_a_match_in_every_score_tier() -> None:
    """Section 4's three lines, and that they really are three different tiers.

    The prompts come from the run itself, so this cannot drift out of step with
    what the section sends; the tiers come from the resolver, so a change in the
    scoring policy fails here rather than being absorbed by a regenerated golden.
    """
    resolver = EntityResolver.from_file(LEXICON)
    printed = transcript_of("every_score_tier_resolves_and_names_itself")

    scored = set()
    for _, prompt in demo.ONE_PROMPT_PER_TIER:
        match = resolver.transform(prompt, "de-DE").matches[0]
        scored.add(match.score_tier)
        assert collapsed(demo.render_match(match)) in printed, (
            f"the section does not show what {prompt!r} resolves to: {match}"
        )

    assert scored == set(ScoreTier), (
        f"the section's prompts cover {sorted(tier.value for tier in scored)}, not "
        f"every score tier"
    )


def test_the_transcript_names_the_entry_and_the_filter_that_answered() -> None:
    """Section 5's two facts, pinned by name: the entry line and the filter line.

    These are the two the epic exists for. The entry has to be legible as a field
    of its own — an integrating developer decides which of entity and entry to
    key on by reading exactly this — and the filter has to appear verbatim,
    because a service pastes it into a query.
    """
    resolver = EntityResolver.from_file(LEXICON)
    printed = transcript_of("two_entries_resolve_to_one_entity_with_their_own_filters")

    answered = [
        resolver.transform(prompt, "de-DE").matches[0]
        for prompt in demo.TWO_PROMPTS_FOR_ONE_ENTITY
    ]

    assert {match.canonical_id for match in answered} == {"product"}, (
        f"the section's prompts no longer both answer product: {answered}"
    )
    for match in answered:
        assert f"entry={match.entry_id}" in printed, (
            f"the section does not name the entry that answered: {match.entry_id}"
        )
        assert f"filter={{{demo.render_filter(match.metadata)}}}" in printed, (
            f"the section does not carry {match.entry_id}'s filter: {match.metadata}"
        )


def test_the_transcript_spells_a_boolean_filter_the_way_the_lexicon_does() -> None:
    """`true`, not `True`, and read off the lexicon file rather than assumed.

    The document is parsed here to find a boolean an entry really declares, so
    this cannot pass by testing a spelling nothing in the corpus uses. An author
    reading `True` has to stop and work out whether they are looking at their own
    file or at Python's rendering of it, which is the whole trust this section
    is meant to build.
    """
    declared = json.loads(LEXICON.read_text(encoding="utf-8"))["entities"]
    booleans = {
        key: value
        for entry in declared.values()
        for key, value in entry.get("metadata", {}).items()
        if isinstance(value, bool)
    }
    printed = transcript_of("two_entries_resolve_to_one_entity_with_their_own_filters")

    assert booleans, (
        "no entry in the example lexicon declares a boolean filter value, so this "
        "section cannot show the spelling it claims to"
    )
    for key, value in booleans.items():
        assert f"{key}={str(value).lower()}" in printed, (
            f"the section does not render {key} as JSON spells it: {value!r}"
        )
        assert f"{key}={value}" not in printed, (
            f"the section renders {key} with Python's spelling, {value!r}"
        )


def test_the_transcript_shows_both_halves_of_typo_tolerance() -> None:
    """Section 6's contrast, resolved here rather than read off the golden.

    Both halves matter. A demonstration that only shows tolerance succeeding
    tells a reader nothing about its boundary, so the section is only honest if
    the same prompt really does come back empty with the keyword off — and that
    is asserted against the resolver, not against the transcript's own wording.
    """
    prompt = demo.A_PROMPT_WITH_A_TYPO
    tolerant = EntityResolver.from_file(LEXICON).transform(prompt, "de-DE")
    exact_only = EntityResolver.from_file(LEXICON, fuzzy=False).transform(
        prompt, "de-DE"
    )
    printed = transcript_of("a_typo_carries_its_correction_and_fuzzy_off_does_not")

    assert len(tolerant.matches) == 1, f"the typo no longer resolves: {tolerant}"
    assert not exact_only.matches, f"the typo resolves with fuzzy off: {exact_only}"

    match = tolerant.matches[0]
    assert match.correction is not None, "the fuzzy match carries no correction"
    assert f'correction="{match.correction}"' in printed, (
        f"the section does not name what was typed: {match.correction!r}"
    )
    assert collapsed(demo.render_match(match)) in printed, (
        f"the section does not show the match tolerance produced: {match}"
    )


def test_the_transcript_names_the_locale_that_answered_each_request() -> None:
    """Section 7's summary line, resolved here rather than read off the golden.

    The cases come from the run, so the test cannot drift out of step with what
    the section sends, and each locale is resolved against the real fallback
    policy. A change that made every request answer in its own locale — or in the
    default regardless — fails here rather than being absorbed by a regenerated
    transcript.
    """
    resolver = EntityResolver.from_file(LEXICON)
    printed = transcript_of("an_undeclared_locale_variant_walks_the_fallback_chain")

    walked = []
    for requested, prompt, expected in demo.THREE_LOCALE_REQUESTS:
        report = resolver.transform(prompt, requested)
        assert report.locale == expected, (
            f"{prompt!r} requested in {requested} was answered by {report.locale}, "
            f"not {expected}"
        )
        walked.append(f"{requested} → {report.locale}")

    assert any(
        requested != answered for requested, _, answered in demo.THREE_LOCALE_REQUESTS
    ), (
        "every request was answered in its own locale, so the section shows no "
        "fallback at all"
    )
    assert ", ".join(walked) in printed, (
        f"the section does not name which locale answered each request: {walked}"
    )


def test_the_transcript_keeps_every_span_on_the_text_as_typed() -> None:
    """Section 8's claim, and the only way to demonstrate it.

    Matching folds a Latin diacritic; the span must not. So both spellings are
    resolved here and each span is sliced out of the prompt it came from — the
    accented prompt must give the accent back, the plain one must not. A span
    computed against the folded text would be off by one from the accent onward
    and this would catch it.
    """
    resolver = EntityResolver.from_file(LEXICON)
    printed = transcript_of("normalization_folds_accents_and_preserves_arabic")

    forms = set()
    for prompt in demo.TWO_SPELLINGS_OF_ONE_LATIN_FORM:
        match = resolver.transform(prompt, "de-DE").matches[0]
        start, end = match.span
        forms.add(match.surface_form)
        assert f'prompt[{start}:{end}] == "{prompt[start:end]}"' in printed, (
            f"the section does not show {prompt!r} sliced by its own span"
        )

    assert len(forms) == 1, (
        f"the two spellings resolved to different declared forms {forms}, so the "
        f"section is not showing one form matched two ways"
    )
    assert len(set(demo.TWO_SPELLINGS_OF_ONE_LATIN_FORM)) == 2, (
        "the two prompts are the same string, so no accent is being folded"
    )


def test_the_transcript_matches_arabic_with_its_script_intact() -> None:
    """Script-preserving means a hamza is a letter, not a mark to discard.

    Both halves are resolved here: the form as written matches, and the same form
    with its hamza replaced by a bare alef does not. A normalization policy that
    stripped everything to ASCII would resolve both, and the section would be
    claiming a policy lexiqr does not have.
    """
    resolver = EntityResolver.from_file(LEXICON)
    printed = transcript_of("normalization_folds_accents_and_preserves_arabic")

    as_written = resolver.transform(demo.AN_ARABIC_PROMPT, "ar-EG")
    stripped = resolver.transform(demo.THE_SAME_ARABIC_WITHOUT_ITS_HAMZA, "ar-EG")

    assert len(as_written.matches) == 1, "the Arabic prompt no longer resolves"
    assert not stripped.matches, (
        f"Arabic resolved with its hamza stripped, so matching is not "
        f"script-preserving: {stripped.matches}"
    )
    assert collapsed(demo.render_match(as_written.matches[0])) in printed, (
        "the section does not show the Arabic match the resolver produces"
    )
    assert as_written.matches[0].surface_form in printed, (
        "the Arabic surface form does not appear in the transcript with its script"
    )


def test_the_run_survives_a_default_stdout_encoding_that_cannot_hold_arabic() -> None:
    """The reason the driver reconfigures stdout, watched rather than asserted in prose.

    A developer on a Windows console meets a code page that cannot encode Arabic,
    and would get a `UnicodeEncodeError` instead of a transcript. Forcing an
    ASCII default here reproduces that without needing Windows. The
    reconfiguration is inside the driver — the import-safety test is what keeps it
    from drifting up to module level.
    """
    result = subprocess.run(
        [sys.executable, str(RUN)],
        cwd=REPO_ROOT,
        capture_output=True,
        env={**os.environ, "PYTHONIOENCODING": "ascii"},
    )

    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert demo.AN_ARABIC_PROMPT.encode("utf-8") in result.stdout, (
        "the run exited zero but its Arabic did not reach stdout"
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


# --- The render helper. Hand-built reports in, expected lines out: no
# --- subprocess, no lexicon, no resolver. This is why the helper is a named
# --- function in the run rather than a private detail, and why the module is
# --- import-safe. A format regression fails here, at the format, rather than in
# --- whichever section happened to show it first.


#: The plainest match there is: an exact, preferred, de-DE hit by an entry that is
#: its own entity, carrying no filter and no correction.
AN_EXACT_MATCH = EntityMatch(
    canonical_id="product",
    entry_id="product",
    surface_form="flooff",
    span=(7, 13),
    score_tier=ScoreTier.PREFERRED,
    matched_locale="de-DE",
)


def a_match(**overrides: Any) -> EntityMatch:
    """The plain match with some of its fields replaced by name."""
    return replace(AN_EXACT_MATCH, **overrides)


def test_the_render_helper_names_what_resolved_and_how_well() -> None:
    """The line every section's result is read off: entity, form, span, tier, locale.

    Deliberately not the CLI's renderer, which is private to the CLI and spends
    three to five lines per match — across twelve sections that transcript would
    be unreadable. Section 12 shows the CLI's format honestly by running the
    real CLI.
    """
    rendered = demo.render_match(a_match())

    assert rendered == (
        'product ← "flooff"  span=(7, 13)  tier=preferred  locale=de-DE'
    )


def test_the_render_helper_names_the_entry_only_when_it_is_not_the_entity() -> None:
    """The distinction an integrating developer has to key on, made visible.

    An entry that *is* its entity has one name, so repeating it would make every
    match in every lexicon read as though something more complicated were going
    on. An entry that resolves to a shared entity has two, and which of them a
    service keys on is the whole question section 5 is about.
    """
    plain = demo.render_match(a_match())
    shared = demo.render_match(
        a_match(canonical_id="product", entry_id="movie", surface_form="filme")
    )

    assert "entry=" not in plain, f"a plain entry named itself twice: {plain}"
    assert shared == (
        'product ← "filme"  span=(7, 13)  tier=preferred  locale=de-DE  entry=movie'
    )


def test_the_render_helper_shows_a_filter_in_the_spelling_its_author_used() -> None:
    """`true`, not `True` — the reader is reading this to learn about their file.

    A boolean is the one value where Python and JSON disagree, and echoing
    Python's spelling would be a small lie in exactly the place that must not
    tell one. A multi-valued key joins on a pipe, the separator the CLI uses and
    the one a filter value cannot contain.
    """
    rendered = demo.render_match(
        a_match(
            entry_id="series",
            surface_form="serien",
            metadata=Metadata(
                {"episodic": True, "seasons": 4, "genre": ("drama", "thriller")}
            ),
        )
    )

    assert rendered.endswith(
        "  entry=series  filter={episodic=true, genre=drama|thriller, seasons=4}"
    ), rendered


def test_the_render_helper_omits_a_filter_an_entry_never_declared() -> None:
    """An empty mapping is absent, not `filter={}`.

    lexiqr hands a match an empty metadata bag rather than `None` so consuming
    code needs no guard — but a line that says nothing is a line a reader has to
    read past, so the transcript prints one only when there is a filter.
    """
    assert "filter=" not in demo.render_match(a_match())


def test_the_render_helper_shows_a_correction_only_when_one_was_applied() -> None:
    """A fuzzy match names what the user typed; an exact one has nothing to name.

    The correction is the text the span points at, so a reader can see both the
    misspelling and the declared form it resolved to on one line — which is what
    section 6 turns on.
    """
    corrected = demo.render_match(a_match(span=(0, 5), correction="floof"))

    assert corrected.endswith('correction="floof"'), corrected
    assert "correction=" not in demo.render_match(a_match())
