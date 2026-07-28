"""A full sample run: one command that demonstrates lexiqr's whole contract.

    uv run python examples/demo.py

Each section states a claim, prints what lexiqr actually produced, and asserts
it. So this is a verification as well as a transcript: a section whose claim
turns out to be false raises, and the run exits non-zero naming the section that
broke. Reading the output tells you what the library does; a zero exit code
tells you it still does it.

It resolves `medien.lexicon.json` — a German media tenant with three locales,
two entries resolving to one `product` entity with distinguishing metadata, an
Austrian variant, plurals, alternates, an accented form, Arabic, a plain entry
carrying neither target nor metadata, and a multi-word label containing a
shorter one.

**Read it top to bottom, and lift what you need.** It is deliberately one flat
file — its render helper, its sections, then the driver — rather than a tidy
package, because its value is being a thing you can read in one sitting and copy
a section out of. It imports nothing but `lexiqr` and the standard library, and
finds its lexicon relative to its own location, so it runs against an installed
wheel from any working directory.

Nothing here prints or resolves at import time: the module defines constants and
functions, and every effect happens inside `main`. That is what lets the test
suite import it to exercise the render helper directly, and what keeps the
golden transcript honest — an import-time side effect would be output nobody
declared.

The full output is committed beside this file as `demo.golden.txt`, and the test
suite compares the two. After an intended change to the transcript, regenerate
it rather than hand-editing:

    uv run python examples/demo.py > examples/demo.golden.txt
"""

from __future__ import annotations

import io
import sys
import textwrap
from pathlib import Path
from typing import Any, Protocol, cast

from lexiqr import (
    EntityMatch,
    EntityResolver,
    Lexicon,
    Metadata,
    MetadataValue,
    ScoreTier,
    ValidationError,
)

#: The tenant lexicon every section resolves against, found relative to this
#: file so the working directory is irrelevant.
LEXICON = Path(__file__).resolve().parent / "medien.lexicon.json"

#: How the lexicon is named in the transcript. Spelled from the path's own parts
#: rather than printed as-is: an absolute path would make the output depend on
#: the machine it ran on, and the golden would never match twice.
LEXICON_LABEL = "/".join(LEXICON.parts[-2:])

#: The transcript's width and the column its values start in. Fixed rather than
#: read from the terminal — the golden must not depend on the window it was
#: rendered in.
WIDTH = 88
LABEL_WIDTH = 10

HEADER = (
    "lexiqr — a sample run: every claim printed, every claim asserted.",
    f"lexicon: {LEXICON_LABEL}",
)

CLOSING = "OK: every section held."


# --- Rendering ---------------------------------------------------------------


def emit(label: str, text: str) -> None:
    """One labelled line of the transcript, wrapped to a fixed width.

    Every line a section prints goes through here, so the transcript has one
    shape: a short label naming what is being shown, and the value beside it.
    """
    print(
        textwrap.fill(
            text,
            width=WIDTH,
            initial_indent=f"{label:<{LABEL_WIDTH}}",
            subsequent_indent=" " * LABEL_WIDTH,
            break_long_words=False,
            break_on_hyphens=False,
        )
    )


def render_match(match: EntityMatch) -> str:
    """One entity match as one dense line: what resolved, and how well.

    The seam every section's result is read off, so it is a named function rather
    than a private detail — a unit test over it is a test of the format a reader
    sees, not of an internal.

    Deliberately *not* the CLI's report renderer. That one is private to the CLI
    and spends three to five lines per match; across twelve sections it would
    make this transcript unreadable. Section 12 shows the CLI's own format
    honestly, by running the real CLI.

    Total over the match type, the same way the CLI's renderer is: the fields a
    match only sometimes carries — the entry that answered, the filter it
    carried, the correction that was applied — are printed only when they say
    something, so a plain lexicon reads exactly as it did before those features
    existed.
    """
    line = (
        f'{match.canonical_id} ← "{match.surface_form}"'
        f"  span={match.span}"
        f"  tier={match.score_tier.value}"
        f"  locale={match.matched_locale}"
    )
    if match.entry_id != match.canonical_id:
        line += f"  entry={match.entry_id}"
    if match.metadata:
        line += f"  filter={{{render_filter(match.metadata)}}}"
    if match.correction is not None:
        line += f'  correction="{match.correction}"'
    return line


def render_filter(metadata: Metadata) -> str:
    """An entry's filter as `key=value` pairs, in the spelling its author used.

    `Metadata` already iterates in sorted key order, so this reads that order
    rather than imposing one of its own — which is what makes two runs of this
    command produce the same text.
    """
    return ", ".join(f"{key}={render_filter_value(metadata[key])}" for key in metadata)


def render_filter_value(value: MetadataValue) -> str:
    """One filter value, spelled the way the lexicon file spells it.

    A boolean is the one place Python and JSON disagree — `True` against `true` —
    and a reader is reading this line to learn what their own *file* does, so
    echoing a spelling that is not in the file would be a small lie in exactly
    the tool that must not tell one. Asked before numbers, since `bool`
    subclasses `int`. A set of values joins on a pipe, the separator the CLI uses
    and one a filter value cannot contain.
    """
    if isinstance(value, tuple):
        return "|".join(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def heading(number: int, title: str) -> None:
    """The numbered rule that opens a section."""
    print()
    print(f"--- {number}. {title} ---")
    print()


# --- The sections ------------------------------------------------------------


def a_lexicon_loads_from_a_file() -> None:
    """A tenant lexicon loads from a file: validation is construction [C2]

    The first thing an integrating developer does, and the first thing that can
    go wrong. There is no separate validate step to forget: the object handed
    back has already been checked.
    """
    lexicon = Lexicon.from_file(LEXICON)

    entities = sorted({entry.canonical_id for entry in lexicon.entries.values()})
    locales = sorted(
        {locale for entry in lexicon.entries.values() for locale in entry.locales}
    )

    emit(
        "claim",
        "Lexicon.from_file either hands back a lexicon lexiqr can trust or raises "
        "ValidationError naming where the document is wrong. Validation is "
        "construction, so a caller holding a lexicon has nothing left to check.",
    )
    emit("lexicon", LEXICON_LABEL)
    emit("entries", ", ".join(sorted(lexicon.entries)))
    emit("entities", ", ".join(entities))
    emit("locales", ", ".join(locales))
    emit("default", lexicon.default_locale)
    emit(
        "held",
        "the loader returned rather than raised, and that verdict is the "
        f"validation. The {len(lexicon.entries)} entries it read resolve to "
        f"{len(entities)} entities, so more than one entry shares an entity, and "
        "the declared default is a locale the lexicon really authors.",
    )

    assert lexicon.entries, "a lexicon that loaded declares at least one entry"
    assert all(entry.locales for entry in lexicon.entries.values()), (
        "every entry came back carrying the locales it declares; nothing was "
        "silently dropped"
    )
    assert len(entities) < len(lexicon.entries), (
        f"{len(lexicon.entries)} entries resolve to {len(entities)} entities, so "
        f"at least two of them share one — which is what makes this lexicon "
        f"worth demonstrating"
    )
    assert lexicon.default_locale in locales, (
        f"the declared default {lexicon.default_locale!r} is one of the locales "
        f"the lexicon authors ({', '.join(locales)})"
    )


#: A lexicon with one ordinary authoring mistake in it: entry "movie" writes its
#: de-DE alternates as a bare string where the format wants an array of labels.
#: Written out here, and handed to the loader in memory, so a reader can see
#: exactly what is being refused without opening a second file.
A_LEXICON_WITH_A_MISTAKE: dict[str, Any] = {
    "schemaVersion": "1",
    "defaultLocale": "de-DE",
    "entities": {
        "movie": {
            "canonicalId": "product",
            "locales": {
                "de-DE": {
                    "preferred": {"singular": "film", "plural": "filme"},
                    "alternates": "spielfilm",
                }
            },
        }
    },
}


def a_rejected_lexicon_names_the_entry_locale_and_field() -> None:
    """A rejected lexicon names the entry, locale, and field at fault [C3]

    The other half of "validation is construction", and the first real question
    a lexicon author has about the format: what a mistake in my own file will
    look like.
    """
    emit(
        "claim",
        "A document lexiqr refuses is refused with coordinates. ValidationError "
        "carries the entry, the locale, and the field at fault as attributes, so "
        "a service can route the failure, and repeats them in one sentence a "
        "lexicon author can act on without reading any Python.",
    )
    emit(
        "document",
        'entry "movie", locale de-DE, with `"alternates": "spielfilm"` — a bare '
        "string where the format wants an array of labels.",
    )

    try:
        Lexicon.from_dict(A_LEXICON_WITH_A_MISTAKE)
    except ValidationError as invalid:
        rejected = invalid
    else:
        raise AssertionError(
            "the loader accepted a document that is not a valid lexicon; "
            "validation is construction only if construction can refuse"
        )

    emit("raised", type(rejected).__name__)
    emit("entry", rejected.canonical_id or "(none)")
    emit("locale", rejected.locale or "(none)")
    emit("field", rejected.field or "(none)")
    emit("message", str(rejected))
    emit(
        "held",
        "the loader refused the document rather than handing back a half-checked "
        "one, and the refusal names all three coordinates — both as attributes to "
        "branch on and in the message an author reads.",
    )

    assert rejected.canonical_id == "movie", (
        f"the refusal names the entry at fault, not {rejected.canonical_id!r}"
    )
    assert rejected.locale == "de-DE", (
        f"the refusal names the locale at fault, not {rejected.locale!r}"
    )
    assert rejected.field == "alternates", (
        f"the refusal names the field at fault, not {rejected.field!r}"
    )
    for coordinate in ("movie", "de-DE", "alternates"):
        assert coordinate in str(rejected), (
            f"the message an author reads does not mention {coordinate!r}: {rejected}"
        )


def an_exact_match_reports_entity_form_span_and_tier() -> None:
    """An exact match reports the entity, the form, the span, and the tier [C4]

    The first match a reader sees, and the moment an integrating developer
    decides whether the report's shape fits their service. The span is used to
    slice the *original* prompt, so it is visible that offsets index the text the
    user typed rather than a normalized copy of it.
    """
    prompt = "wo ist die rechnung"
    report = EntityResolver.from_file(LEXICON).transform(prompt, "de-DE")
    match = report.matches[0]
    start, end = match.span

    emit(
        "claim",
        "transform() returns a typed match report: the prompt it was given, the "
        "locale that resolved it, and an ordered list of matches — each naming "
        "the entity, the surface form it matched, its character span, and its "
        "score tier.",
    )
    emit("prompt", f'"{report.prompt}"')
    emit("locale", report.locale)
    emit("matches", str(len(report.matches)))
    emit("match", render_match(match))
    emit("sliced", f'prompt[{start}:{end}] == "{prompt[start:end]}"')
    emit(
        "held",
        "the span indexes the prompt as typed, so slicing the original text by it "
        "gives back exactly the surface form the match reports — no second search, "
        "no normalized copy to reconcile.",
    )

    assert len(report.matches) == 1, f"expected one match, got {report.matches}"
    assert report.prompt == prompt, "the report carries the prompt it was handed"
    assert report.locale == "de-DE", f"the report resolved via {report.locale!r}"
    assert match.canonical_id == "invoice", (
        f"'rechnung' resolves to the invoice entity, not {match.canonical_id!r}"
    )
    assert match.score_tier is ScoreTier.PREFERRED, (
        f"a tenant's preferred singular scores preferred, not {match.score_tier}"
    )
    assert prompt[start:end] == match.surface_form, (
        f"the span slices the original prompt to {prompt[start:end]!r}, but the "
        f"match reports {match.surface_form!r}"
    )


#: One prompt per score tier, in the order the ranking puts them: the tenant's
#: preferred plural, an alternate label they also accept, and the entry ID their
#: users never see but a prompt may still name outright.
ONE_PROMPT_PER_TIER = (
    (ScoreTier.PREFERRED, "wo sind die filme"),
    (ScoreTier.ALTERNATE, "wo ist der spielfilm"),
    (ScoreTier.CANONICAL, "wo sind die series"),
)


def every_score_tier_resolves_and_names_itself() -> None:
    """Preferred, alternate and canonical each resolve and each name their tier [C4]

    Score tier is the whole of lexiqr's ranking: a deterministic ordering, not a
    similarity number a caller has to threshold.
    """
    resolver = EntityResolver.from_file(LEXICON)

    emit(
        "claim",
        "A match names the tier it scored in, and the ranking is fixed: preferred "
        "beats alternate beats canonical. A tenant's own vocabulary outranks a "
        "synonym they also accept, and both outrank the entry identifier their "
        "users never see.",
    )

    observed: list[ScoreTier] = []
    for expected, prompt in ONE_PROMPT_PER_TIER:
        match = resolver.transform(prompt, "de-DE").matches[0]
        observed.append(match.score_tier)
        emit(expected.value, f'"{prompt}" → {render_match(match)}')

    emit(
        "held",
        "all three tiers were observed, each one named by the match that came "
        "back rather than inferred from which prompt was sent.",
    )

    assert set(observed) == set(ScoreTier), (
        f"the three prompts scored {[tier.value for tier in observed]}; a section "
        f"that resolved one tier three times would demonstrate nothing"
    )
    for (expected, prompt), scored in zip(ONE_PROMPT_PER_TIER, observed, strict=True):
        assert scored is expected, (
            f"{prompt!r} was meant to show the {expected.value} tier and scored "
            f"{scored.value}"
        )


#: Two things this tenant's users say, which their backend stores as one entity.
#: "movie" and "series" are two *entries* resolving to `product`; what tells them
#: apart is the filter each carries.
TWO_PROMPTS_FOR_ONE_ENTITY = ("zeig mir die filme", "zeig mir die serien")


def two_entries_resolve_to_one_entity_with_their_own_filters() -> None:
    """Two entries resolve to one entity, each with its own filter [C19]

    The reason a tenant's five words for one database concept stop needing a
    lookup table in the integrating developer's own service.
    """
    resolver = EntityResolver.from_file(LEXICON)

    emit(
        "claim",
        "Several entries may resolve to one entity. Every match names the entity "
        "a backend queries, the entry that answered, and that entry's filter — "
        "carried verbatim and never interpreted — so a service builds its query "
        "from the match report instead of keeping a per-tenant table of its own.",
    )

    answered = []
    for prompt in TWO_PROMPTS_FOR_ONE_ENTITY:
        match = resolver.transform(prompt, "de-DE").matches[0]
        answered.append(match)
        emit("match", f'"{prompt}" → {render_match(match)}')

    emit(
        "spelling",
        "the boolean filter value reads `episodic=true` — the spelling the lexicon "
        "file uses, not Python's `True`. A reader is here to learn what their own "
        "document says.",
    )
    emit(
        "held",
        "both matches name one entity, and each names its own entry and its own "
        "filter. The entry is a field of its own, so a service knows which of the "
        "two to key on; the filter is the tenant's own words, so it can go "
        "straight into a query.",
    )

    entities = {match.canonical_id for match in answered}
    assert entities == {"product"}, (
        f"both prompts were meant to answer one entity and answered {entities}"
    )
    assert len({match.entry_id for match in answered}) == len(answered), (
        "the two matches came back under one entry ID, so nothing distinguishes "
        "them and the section shows nothing"
    )
    assert len({match.metadata for match in answered}) == len(answered), (
        "the two entries carry the same filter, so a service could not tell which "
        "of them a match meant"
    )

    values = [value for match in answered for value in match.metadata.values()]
    assert any(isinstance(value, tuple) for value in values), (
        "no entry carries a multi-valued key, so the section cannot show one"
    )
    assert any(isinstance(value, bool) for value in values), (
        "no entry carries a boolean, so the section cannot show its spelling"
    )
    rendered = " ".join(render_filter(match.metadata) for match in answered)
    assert "=true" in rendered and "=True" not in rendered, (
        f"a boolean filter value is not rendered the way the lexicon spells it: "
        f"{rendered}"
    )


#: A misspelling of the declared plural "filme", one deletion away from it and so
#: inside the edit budget a six-character form earns.
A_PROMPT_WITH_A_TYPO = "zeig mir die flme"


def a_typo_carries_its_correction_and_fuzzy_off_does_not() -> None:
    """A typo resolves and carries its correction; with fuzzy off it does not [C5]

    Typo tolerance is the claim most often taken on faith, because a
    demonstration that only shows it succeeding says nothing about where it
    stops. So the same prompt is resolved twice, and the contrast is the point.
    """
    tolerant = EntityResolver.from_file(LEXICON)
    exact_only = EntityResolver.from_file(LEXICON, fuzzy=False)

    with_tolerance = tolerant.transform(A_PROMPT_WITH_A_TYPO, "de-DE")
    without = exact_only.transform(A_PROMPT_WITH_A_TYPO, "de-DE")
    match = with_tolerance.matches[0]
    start, end = match.span

    emit(
        "claim",
        "Typo tolerance is on by default, inside a length-aware edit budget. A "
        "fuzzy match resolves to the form the tenant declared and carries the "
        "correction — the text the user actually typed — so a service can echo "
        "the user's words while querying the tenant's. `fuzzy=False` turns the "
        "pass off entirely.",
    )
    emit("prompt", f'"{A_PROMPT_WITH_A_TYPO}"')
    emit("tolerant", render_match(match))
    emit("typed", f'prompt[{start}:{end}] == "{A_PROMPT_WITH_A_TYPO[start:end]}"')
    emit(
        "exact",
        f"EntityResolver.from_file(..., fuzzy=False) → "
        f"{len(without.matches)} matches, resolved via {without.locale}",
    )
    emit(
        "held",
        "the same prompt resolves with tolerance on and resolves to nothing with "
        "it off. A reader can see what the fuzzy pass is doing, and what turning "
        "it off costs them, rather than taking either on faith.",
    )

    assert len(with_tolerance.matches) == 1, (
        f"the typo was meant to resolve to one match, and gave {with_tolerance.matches}"
    )
    assert match.correction == A_PROMPT_WITH_A_TYPO[start:end], (
        f"the correction {match.correction!r} is not the text the span points at, "
        f"{A_PROMPT_WITH_A_TYPO[start:end]!r}"
    )
    assert match.correction != match.surface_form, (
        f"the correction and the surface form are both {match.correction!r}, so "
        f"this prompt is not a typo at all and the section shows nothing"
    )
    assert not without.matches, (
        f"the same prompt resolved with fuzzy off, so the two halves of this "
        f"section say the same thing: {without.matches}"
    )
    assert without.prompt == A_PROMPT_WITH_A_TYPO, (
        "an exact-only resolver still returns a report naming the prompt it read"
    )


#: Three requests, and the locale each one is answered by. `de-CH` is a variant
#: the lexicon never declares; `de-AT` is one it declares on a single entry, so
#: the same requested locale answers its own prompt for the form it authors and
#: falls through to the default for the form it does not.
THREE_LOCALE_REQUESTS = (
    ("de-CH", "wo ist der film", "de-DE"),
    ("de-AT", "wo ist die faktura", "de-AT"),
    ("de-AT", "wo ist die rechnung", "de-DE"),
)


def an_undeclared_locale_variant_walks_the_fallback_chain() -> None:
    """An undeclared locale variant resolves, and the report names what answered [C6]

    What happens when a caller's users request `de-AT` and the tenant authored
    `de-DE`. The answer has to be traceable, not merely successful.
    """
    lexicon = Lexicon.from_file(LEXICON)
    resolver = EntityResolver(lexicon)
    declared = sorted(
        {locale for entry in lexicon.entries.values() for locale in entry.locales}
    )

    emit(
        "claim",
        "A caller states the locale and lexiqr never guesses it. When the "
        "requested locale produces no match, resolution walks a chain — the exact "
        "locale, then that language's other variants in tag order, then the "
        "declared default — and stops at the first locale that answers. The "
        "report names that locale.",
    )
    emit(
        "declared",
        f"{', '.join(declared)} — default {lexicon.default_locale}, with de-AT "
        f"authored on one entry only",
    )

    walked = []
    for requested, prompt, _ in THREE_LOCALE_REQUESTS:
        report = resolver.transform(prompt, requested)
        walked.append((requested, prompt, report))
        emit(requested, f'"{prompt}" → {render_match(report.matches[0])}')

    emit(
        "answered",
        ", ".join(f"{requested} → {report.locale}" for requested, _, report in walked),
    )
    emit(
        "held",
        "a variant the lexicon never declares is answered by a sibling or by the "
        "default; a variant it does author answers its own prompts and falls "
        "through only for the forms it does not declare. Either way the report "
        "says which locale it was.",
    )

    for (requested, prompt, report), (_, _, expected) in zip(
        walked, THREE_LOCALE_REQUESTS, strict=True
    ):
        assert len(report.matches) == 1, (
            f"{prompt!r} in {requested} was meant to resolve and gave {report.matches}"
        )
        assert report.locale == expected, (
            f"{prompt!r} requested in {requested} was answered by "
            f"{report.locale}, not {expected}"
        )
        assert report.matches[0].matched_locale == report.locale, (
            "the match names a different locale than the report it sits in"
        )

    answered = {(requested, report.locale) for requested, _, report in walked}
    assert any(requested != locale for requested, locale in answered), (
        "every request was answered in the locale it asked for, so nothing here "
        "demonstrates a fallback chain"
    )
    assert any(requested == locale for requested, locale in answered), (
        "no request was answered by the locale it asked for, so the chain's "
        "stopping point at the more specific locale is not visible"
    )


# --- The driver --------------------------------------------------------------


class Section(Protocol):
    """One section of the run: it prints its claim, its result, and asserts it.

    A protocol rather than a plain `Callable`, because the driver reads two
    things off a section besides calling it: its `__name__`, to name the section
    that failed, and the first line of its docstring, which is its title in the
    transcript.
    """

    __name__: str

    def __call__(self) -> None: ...


#: Every section, in the order the transcript prints them. Position is the
#: section number, so adding one here is the whole edit.
SECTIONS: tuple[Section, ...] = (
    a_lexicon_loads_from_a_file,
    a_rejected_lexicon_names_the_entry_locale_and_field,
    an_exact_match_reports_entity_form_span_and_tier,
    every_score_tier_resolves_and_names_itself,
    two_entries_resolve_to_one_entity_with_their_own_filters,
    a_typo_carries_its_correction_and_fuzzy_off_does_not,
    an_undeclared_locale_variant_walks_the_fallback_chain,
)


def title_of(section: Section) -> str:
    """A section's title: the first line of its docstring."""
    documentation = section.__doc__
    assert documentation is not None, f"{section.__name__} has no docstring to title it"
    return documentation.strip().splitlines()[0].strip()


def main() -> int:
    """Print every section, assert every claim, and report whether they held."""
    # Arabic surface forms are part of what this run demonstrates, and a Windows
    # console defaults to a code page that cannot encode them. The cast is here
    # because `reconfigure` is a `TextIOWrapper` method the standard streams'
    # type stub does not advertise.
    cast(io.TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")

    for line in HEADER:
        print(line)

    for number, section in enumerate(SECTIONS, start=1):
        heading(number, title_of(section))
        try:
            section()
        except AssertionError as failed:
            print()
            print(f"FAIL in section {number} ({section.__name__}): {failed}")
            return 1

    print()
    print(CLOSING)
    return 0


if __name__ == "__main__":
    sys.exit(main())
