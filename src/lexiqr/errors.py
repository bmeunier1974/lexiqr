"""The errors lexiqr raises — public API, semver-governed (ADR 0002).

`ValidationError` is what an integrating developer catches when a tenant's
lexicon is wrong. Its three coordinates — canonical ID, locale, field — are
what makes the failure actionable: they let the developer tell the lexicon's
owner exactly where to look without ever debugging lexiqr. The CLI renders
this error verbatim, so precision here is precision everywhere.

Coordinates a given failure does not have are `None`: a bad `schemaVersion` is
a fault of the document as a whole, not of any one entity.

`MalformedDocumentError` is the one failure that has no coordinates to have: a
file that is not JSON never became a document, so nothing in it can be pointed
at. It is a `ValidationError` — a caller who only wants "this lexicon cannot be
loaded" writes one `except` — and a distinct type, so a caller who must tell
"your path points at something that is not a lexicon file" from "your lexicon
says the wrong thing" can. The CLI is that caller: the distinction is what its
two exit codes are made of.
"""

from __future__ import annotations

from typing import Any

#: The JSON name of each type a parsed document can hold. Naming what a value
#: turned out to be is half of every type fault lexiqr reports, and it is reported
#: from more than one module — so the wording lives here, with the errors, and "an
#: object" never becomes "a dict" in one message and not another.
_JSON_KINDS = {
    dict: "an object",
    list: "an array",
    str: "a string",
    bool: "a boolean",
    int: "a number",
    float: "a number",
    type(None): "null",
}


def kind(value: Any) -> str:
    """The JSON name for what `value` turned out to be, for an error message."""
    return _JSON_KINDS.get(type(value), f"a {type(value).__name__}")


class ValidationError(Exception):
    """A lexicon was rejected. Says what is wrong, and where.

    The message reads as a sentence naming whichever coordinates apply, so it
    can be pasted into a support ticket unedited.
    """

    def __init__(
        self,
        message: str,
        *,
        canonical_id: str | None = None,
        locale: str | None = None,
        field: str | None = None,
    ) -> None:
        self.message = message
        self.canonical_id = canonical_id
        self.locale = locale
        self.field = field
        super().__init__(message)


class MalformedDocumentError(ValidationError):
    """The file is not JSON, so there is no lexicon document to validate.

    Raised only by the file-loading path — `Lexicon.from_file` and the
    constructors built on it — and never for a document that parsed: a document
    lexiqr could read but had to reject is an ordinary `ValidationError` naming
    the field at fault.
    """
