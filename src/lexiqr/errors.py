"""The errors lexiqr raises — public API, semver-governed (ADR 0002).

`ValidationError` is what an integrating developer catches when a tenant's
lexicon is wrong. Its three coordinates — canonical ID, locale, field — are
what makes the failure actionable: they let the developer tell the lexicon's
owner exactly where to look without ever debugging lexiqr. The CLI renders
this error verbatim, so precision here is precision everywhere.

Coordinates a given failure does not have are `None`: a bad `schemaVersion` is
a fault of the document as a whole, not of any one entity.
"""

from __future__ import annotations


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
