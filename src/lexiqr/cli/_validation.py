"""The pure validation-error renderer — typed error(s) in, string out.

This module owns the whole presentation policy for `lexiqr validate`: how a
lexicon with no errors is confirmed, how multiple errors are ordered and
grouped, and how each fault is laid out. It never touches argv, stdout, or the
filesystem, so it is unit-tested by handing it directly-constructed values.

Core's `ValidationError` message is shown verbatim — its substance is the same
error an integrating developer sees at load time (C14), and the shell must not
re-word or re-classify it. What this module adds is layout: a header that names
the source and counts the faults, deterministic ordering, and one bullet per
error.
"""

from __future__ import annotations

from collections.abc import Sequence

from lexiqr import ValidationError


def render_valid_lexicon(source: str) -> str:
    """Confirm, unambiguously, that `source` loaded as a valid lexicon."""
    return f"{source}: valid lexicon."


def render_validation_errors(source: str, errors: Sequence[ValidationError]) -> str:
    """Render every fault in `source`, deterministically ordered.

    The interface takes a collection: core surfaces one fault at a time today,
    but the renderer does not assume that, so it stays correct if a caller ever
    hands it several.
    """
    ordered = sorted(errors, key=_order_key)
    count = len(ordered)
    noun = "error" if count == 1 else "errors"
    header = f"{source}: invalid lexicon — {count} {noun}."
    return "\n".join([header, *(f"  - {error.message}" for error in ordered)])


def _order_key(error: ValidationError) -> tuple[str, str, str, str]:
    """A total order over faults by their coordinates, then their message.

    Coordinates a fault does not have sort first (an empty string), so
    document-level faults precede entity-level ones and the ordering is stable
    regardless of the order core happened to raise them in.
    """
    return (
        error.canonical_id or "",
        error.locale or "",
        error.field or "",
        error.message,
    )
