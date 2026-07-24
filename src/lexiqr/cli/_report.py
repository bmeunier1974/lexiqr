"""The pure match-report renderer — a typed `MatchReport` in, string out.

Like the validation renderer, this module never touches argv, stdout, or the
filesystem: it consumes the typed report and returns text. Because it renders
the report type rather than the pipeline, fields core populates later surface
here without a structural change.
"""

from __future__ import annotations

from lexiqr import MatchReport


def render_match_report(report: MatchReport) -> str:
    """Render a match report as plain, terminal-legible text."""
    lines = [f'prompt: "{report.prompt}"', f"locale: {report.locale}"]
    if not report.matches:
        lines.append("matches: none")
        return "\n".join(lines)

    lines.append(f"matches: {len(report.matches)}")
    lines.extend(
        f'  {match.canonical_id} ← "{match.surface_form}" '
        f"[{match.span[0]}:{match.span[1]}]"
        for match in report.matches
    )
    return "\n".join(lines)
