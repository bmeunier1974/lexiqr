"""The pure match-report renderer — a typed `MatchReport` in, string out.

Like the validation renderer, this module never touches argv, stdout, or the
filesystem: it consumes the typed report and returns text. Because it renders
the report *type* rather than the pipeline, it is total over that type — every
field a match can carry is rendered when present and omitted when absent, so a
field a later epic populates (a correction, a diverging matched locale) surfaces
here with no structural change. The lines that only sometimes apply — the entry
that answered, the filter it carried, the correction that was applied — are
printed only when they say something, so a lexicon using none of those features
renders exactly as it did before they existed.

Span marking is built from the report's character offsets into the *original*
prompt. The renderer never re-derives a position by searching for the surface
form: accents and casefolding make the original text and the matched form
differ, so searching would mark the wrong characters — or none — and would
reintroduce matching logic on the CLI side of the boundary (ADR 0002).
"""

from __future__ import annotations

from lexiqr import EntityMatch, MatchReport, Metadata

_SPAN_OPEN = "["
_SPAN_CLOSE = "]"

#: How a filter reads on one line: pairs separated by commas, and a set of values
#: joined by pipes — a separator a filter value cannot contain, since the value
#: domain is bounded to the identifier-ish text the schema allows.
_PAIR_SEPARATOR = ", "
_VALUE_SEPARATOR = "|"


def render_match_report(report: MatchReport) -> str:
    """Render a match report as plain, terminal-legible text."""
    if not report.matches:
        return "\n".join(
            [
                f'prompt: "{report.prompt}"',
                f"resolved via: {report.locale}",
                "no match",
            ]
        )

    count = len(report.matches)
    noun = "match" if count == 1 else "matches"
    lines = [
        f'prompt: "{_mark_spans(report.prompt, report.matches)}"',
        f"resolved via: {report.locale}",
        f"{count} {noun}:",
    ]
    for index, match in enumerate(report.matches, start=1):
        lines.append("")
        lines.extend(_render_match(index, match, report.prompt))
    return "\n".join(lines)


def _render_match(index: int, match: EntityMatch, prompt: str) -> list[str]:
    start, end = match.span
    block = [
        f'  [{index}] {match.canonical_id} ← "{match.surface_form}"',
        f"      tier: {match.score_tier.value}   locale: {match.matched_locale}"
        f'   text: "{prompt[start:end]}"',
    ]
    # Both of these are conditional for the same reason `correction` is: a line
    # that says nothing is a line an author has to read past. An entry that *is*
    # its entity has one name, and most entries carry no filter at all — so a
    # lexicon that does not use the feature renders exactly as it did before the
    # feature existed.
    if match.entry_id != match.canonical_id:
        block.append(f"      entry: {match.entry_id}")
    if match.metadata:
        block.append(f"      filter: {_render_filter(match.metadata)}")
    if match.correction is not None:
        block.append(f'      correction: "{match.correction}"')
    return block


def _render_filter(metadata: Metadata) -> str:
    """One line of `key=value` pairs, in sorted key order.

    Sorted so two runs of the same command produce the same text — the same reason
    the canonical serialization sorts. `Metadata` already iterates in that order,
    so this reads it rather than imposing an order of its own.
    """
    return _PAIR_SEPARATOR.join(
        f"{key}={_render_value(metadata[key])}" for key in metadata
    )


def _render_value(value: object) -> str:
    """A filter value in the spelling its author used.

    Booleans are the one case Python and JSON disagree on — `True` against `true`.
    An author reading this line is reading it to find out what their *file* does,
    so echoing a spelling that is not in the file would be a small lie in exactly
    the tool that must not tell one. Asked before numbers, since `bool` subclasses
    `int`.
    """
    if isinstance(value, tuple):
        return _VALUE_SEPARATOR.join(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _mark_spans(prompt: str, matches: tuple[EntityMatch, ...]) -> str:
    """Bracket every matched span in the original prompt, built from offsets.

    Spans are inserted from right to left so each insertion leaves the offsets
    of the spans still to its left untouched. Core resolves overlaps before the
    report is built, so the spans do not overlap.
    """
    marked = prompt
    for start, end in sorted((match.span for match in matches), reverse=True):
        marked = (
            marked[:start] + _SPAN_OPEN + marked[start:end] + _SPAN_CLOSE + marked[end:]
        )
    return marked
