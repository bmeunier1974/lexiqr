"""lexiqr — deterministic resolution of tenant jargon to canonical entities.

The public API is the resolution path — `EntityResolver` and the report types it
returns (ADR 0002) — plus the two things a caller must be able to name without
reaching behind it: the lexicon model `EntityResolver` takes, and the two limits
lexiqr documents.

`Lexicon` (with `Entry`, the named set of forms an entity is keyed by,
`SurfaceForms`, the shape an entry holds per locale, and `Metadata` /
`MetadataValue`, the filter an entry carries) is the declared parameter type of
the constructor, and validation *is* construction —
`Lexicon.from_file` / `from_dict` either return a lexicon core can trust or raise
`ValidationError` naming where the document is wrong. Exporting it lets a lexicon
be loaded, checked, and held on its own, without building a throwaway resolver to
find out whether a tenant's file is valid. `MalformedDocumentError` is the one
load failure with no place in the document to name — the file is not JSON at all
— so a caller can tell a wrong path from a wrong lexicon.

`MAX_PROMPT_LENGTH` and `MAX_SURFACE_FORM_LENGTH` are documented, semver-governed
numbers rather than configuration, so a caller sizing input or generating labels
reads the limit lexiqr actually enforces instead of copying it.

Nothing behind these is public: fallback, index, locale, matcher and normalizer
stay internal, and can change in a patch.
"""

from lexiqr.errors import MalformedDocumentError, ValidationError
from lexiqr.lexicon import MAX_SURFACE_FORM_LENGTH, Entry, Lexicon, SurfaceForms
from lexiqr.metadata import Metadata, MetadataValue
from lexiqr.resolver import MAX_PROMPT_LENGTH, EntityResolver
from lexiqr.serialization import deserialize_report, serialize_report
from lexiqr.types import EntityMatch, MatchReport, ScoreTier

__all__ = [
    "MAX_PROMPT_LENGTH",
    "MAX_SURFACE_FORM_LENGTH",
    "EntityMatch",
    "EntityResolver",
    "Entry",
    "Lexicon",
    "MalformedDocumentError",
    "MatchReport",
    "Metadata",
    "MetadataValue",
    "ScoreTier",
    "SurfaceForms",
    "ValidationError",
    "deserialize_report",
    "serialize_report",
]
