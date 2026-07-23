"""Loading a lexicon document into core's internal model.

Parsing here is deliberately minimal and trusting; validation depth grows
inside this module in a later plan.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lexiqr.errors import ValidationError

#: The one lexicon format version core implements (ADR 0003).
SCHEMA_VERSION = "1"


@dataclass(frozen=True)
class SurfaceForms:
    """The surface forms of one entity in one locale."""

    preferred_singular: str
    preferred_plural: str | None = None
    alternates: tuple[str, ...] = ()


@dataclass(frozen=True)
class Lexicon:
    """A tenant's jargon-to-entity mapping, as core sees it."""

    schema_version: str
    default_locale: str
    entities: dict[str, dict[str, SurfaceForms]]

    @classmethod
    def from_dict(cls, document: dict[str, Any]) -> Lexicon:
        # The version comes first: core cannot interpret a document whose
        # format it does not implement, so it must not try to read one.
        declared = document.get("schemaVersion")
        if declared != SCHEMA_VERSION:
            raise ValidationError(
                f"Unsupported lexicon schemaVersion {declared!r}: this version of "
                f"lexiqr implements schemaVersion {SCHEMA_VERSION!r}.",
                field="schemaVersion",
            )
        entities = {
            canonical_id: {
                locale: _surface_forms(forms)
                for locale, forms in entity.get("locales", {}).items()
            }
            for canonical_id, entity in document.get("entities", {}).items()
        }
        return cls(
            schema_version=document["schemaVersion"],
            default_locale=document["defaultLocale"],
            entities=entities,
        )

    @classmethod
    def from_file(cls, path: str | Path) -> Lexicon:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(document)


def _surface_forms(forms: dict[str, Any]) -> SurfaceForms:
    preferred = forms.get("preferred", {})
    return SurfaceForms(
        preferred_singular=preferred["singular"],
        preferred_plural=preferred.get("plural"),
        alternates=tuple(forms.get("alternates", ())),
    )
