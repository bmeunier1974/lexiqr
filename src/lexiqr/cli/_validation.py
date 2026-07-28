"""The pure load-outcome renderer — a typed outcome in, string out.

This module owns the whole presentation policy for loading a lexicon: how a
lexicon with no errors is confirmed, how the shell's own CLI-level failures are
stamped, and how multiple lexicon faults are ordered, grouped and laid out. It
never touches argv, stdout, or the filesystem, so it is unit-tested by handing
it directly-constructed values.

Core's messages are shown verbatim — their substance is the same error an
integrating developer sees at load time (C14), and the shell must not re-word or
re-classify them, nor keep a second copy of one. What this module adds is
presentation: the ``lexiqr:`` prefix that marks a line as the shell's own
diagnostic, and, for lexicon faults, a header that names the source and counts
the faults, deterministic ordering, and one bullet per error.
"""

from __future__ import annotations

from collections.abc import Sequence

from lexiqr import MalformedDocumentError, ValidationError

#: Stamped on every CLI-level diagnostic, so a line captured out of a build log
#: still names what wrote it. Prefixing is the whole of the shell's contribution
#: to those messages.
_PREFIX = "lexiqr"


def render_valid_lexicon(source: str) -> str:
    """Confirm, unambiguously, that `source` loaded as a valid lexicon."""
    return f"{source}: valid lexicon."


def render_unreadable_source(source: str, unreadable: OSError) -> str:
    """Report that the path the shell was handed cannot be read at all.

    The shell's own failure — the author's path is wrong, not their lexicon — so
    it is phrased so it cannot be mistaken for one, in the operating system's own
    words about the file.
    """
    reason = unreadable.strerror or str(unreadable)
    return f"{_PREFIX}: cannot read {source}: {reason}"


def render_malformed_document(malformed: MalformedDocumentError) -> str:
    """Report that the file is not JSON, in the words core already wrote.

    The sentence — which file, what was expected, at which line and column — is
    core's, carried through untouched, because the lexicon author and the
    integrating developer must read the same one. The prefix is all the shell
    adds.
    """
    return f"{_PREFIX}: {malformed.message}"


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
