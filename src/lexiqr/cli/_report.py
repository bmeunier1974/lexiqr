"""The pure match-report renderer — a typed `MatchReport` in, string out.

Like the validation renderer, this module never touches argv, stdout, or the
filesystem: it consumes the typed report and returns text. Because it renders
the report *type* rather than the pipeline, it is total over that type — every
field a match can carry is rendered when present and omitted when absent, so a
field a later epic populates (a correction, a diverging matched locale) surfaces
here with no structural change.

Span marking is built from the report's character offsets into the *original*
prompt. The renderer never re-derives a position by searching for the surface
form: accents and casefolding make the original text and the matched form
differ, so searching would mark the wrong characters — or none — and would
reintroduce matching logic on the CLI side of the boundary (ADR 0002).
"""

from __future__ import annotations

from lexiqr import EntityMatch, MatchReport

_SPAN_OPEN = "["
_SPAN_CLOSE = "]"


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
    if match.correction is not None:
        block.append(f'      correction: "{match.correction}"')
    return block


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
