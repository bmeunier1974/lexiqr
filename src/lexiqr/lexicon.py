"""Loading a lexicon document into core's internal model.

One entry point in, one validated `Lexicon` — or a `ValidationError` naming
exactly where the document is wrong (ADR 0002, ADR 0003). Callers hand over a
JSON file path or a parsed dict and get back something core can trust; nothing
downstream of here re-checks the data.

Faults are reported with whatever coordinates they have. A bad `entities`
belongs to the document, a bad locale key belongs to an entity, a bad surface
form belongs to an entity *and* a locale — and the coordinates a fault does not
have stay `None` rather than being invented.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lexiqr.errors import ValidationError

#: The one lexicon format version core implements (ADR 0003).
SCHEMA_VERSION = "1"

#: The longest surface form core will accept, in Unicode code points. The schema
#: bounds a surface form below (`minLength: 1`) but not above; core adds the
#: upper bound because a surface form is matched as a whole word and compared
#: under edit distance, so its length is a cost multiplier in every scan. A form
#: far longer than any real label is not data a tenant meant to write — it is
#: what a pathological lexicon looks like — and left unbounded it would make
#: matching pathologically slow. Rejecting it at load turns a request-path hang
#: into a validation-time error the author can fix. Documented in
#: docs/lexicon-semantic-checks.md; changing it is a semver-visible change.
MAX_SURFACE_FORM_LENGTH = 128

#: The subset of BCP 47 the lexicon format accepts, mirroring the published
#: schema's `$defs/locale` — language, optional script, optional region.
_LOCALE = re.compile(r"[A-Za-z]{2,3}(-[A-Za-z]{4})?(-([A-Za-z]{2}|[0-9]{3}))?")

#: Keys the v1 format defines, mirroring the schema's `additionalProperties`
#: bans. A key outside these is a typo, and a typo silently ignored is a
#: surface form the tenant believes is live and isn't.
_DOCUMENT_KEYS = frozenset({"$schema", "schemaVersion", "defaultLocale", "entities"})
_ENTITY_KEYS = frozenset({"locales"})
_SURFACE_FORM_KEYS = frozenset({"preferred", "alternates"})
_PREFERRED_KEYS = frozenset({"singular", "plural"})


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
        declared = document.get("schemaVersion") if isinstance(document, dict) else None
        if declared != SCHEMA_VERSION:
            raise ValidationError(
                f"Unsupported lexicon schemaVersion {declared!r}: this version of "
                f"lexiqr implements schemaVersion {SCHEMA_VERSION!r}.",
                field="schemaVersion",
            )

        _reject_unknown_keys(document, _DOCUMENT_KEYS, "the lexicon document")

        default_locale = document.get("defaultLocale")
        if not isinstance(default_locale, str) or not _LOCALE.fullmatch(default_locale):
            raise _fault(
                "defaultLocale",
                f"is {default_locale!r}, which is not a well-formed locale tag "
                f"(expected BCP 47, e.g. 'de-DE')",
            )

        entities = document.get("entities")
        if not isinstance(entities, dict):
            raise _fault(
                "entities",
                f"must be an object keyed by canonical ID, not {_kind(entities)}",
            )
        if not entities:
            raise _fault(
                "entities", "is empty; a lexicon with no entities resolves nothing"
            )

        parsed = {
            canonical_id: _locales(entity, canonical_id)
            for canonical_id, entity in entities.items()
        }
        _reject_ambiguous_surface_forms(parsed)
        return cls(
            schema_version=SCHEMA_VERSION,
            default_locale=default_locale,
            entities=parsed,
        )

    @classmethod
    def from_file(cls, path: str | Path) -> Lexicon:
        text = Path(path).read_text(encoding="utf-8")
        try:
            document = json.loads(text)
        except json.JSONDecodeError as broken:
            raise ValidationError(
                f"{path} is not valid JSON: {broken.msg} "
                f"(line {broken.lineno}, column {broken.colno})."
            ) from broken
        return cls.from_dict(document)


def _locales(entity: Any, canonical_id: str) -> dict[str, SurfaceForms]:
    if not isinstance(entity, dict):
        raise _fault(
            "entities",
            f"maps {canonical_id!r} to {_kind(entity)}, not an entity object",
            canonical_id=canonical_id,
        )
    _reject_unknown_keys(entity, _ENTITY_KEYS, f"entity {canonical_id!r}", canonical_id)

    locales = entity.get("locales")
    if not isinstance(locales, dict):
        raise _fault(
            "locales",
            f"must be an object keyed by locale tag, not {_kind(locales)}",
            canonical_id=canonical_id,
        )
    if not locales:
        raise _fault(
            "locales",
            "is empty; an entity with no locales can never be matched",
            canonical_id=canonical_id,
        )

    for locale in locales:
        if not _LOCALE.fullmatch(locale):
            raise _fault(
                "locales",
                f"has key {locale!r}, which is not a well-formed locale tag "
                f"(expected BCP 47, e.g. 'de-DE')",
                canonical_id=canonical_id,
                locale=locale,
            )

    return {
        locale: _surface_forms(forms, canonical_id, locale)
        for locale, forms in locales.items()
    }


def _surface_forms(forms: Any, canonical_id: str, locale: str) -> SurfaceForms:
    def fault(field: str, reason: str) -> ValidationError:
        return _fault(field, reason, canonical_id=canonical_id, locale=locale)

    if not isinstance(forms, dict):
        raise fault("locales", f"maps {locale!r} to {_kind(forms)}, not surface forms")
    _reject_unknown_keys(
        forms,
        _SURFACE_FORM_KEYS,
        f"entity {canonical_id!r}, locale {locale!r}",
        canonical_id,
        locale,
    )

    preferred = forms.get("preferred")
    if not isinstance(preferred, dict):
        raise fault("preferred", f"must be an object, not {_kind(preferred)}")
    _reject_unknown_keys(
        preferred,
        _PREFERRED_KEYS,
        f"entity {canonical_id!r}, locale {locale!r}, field 'preferred'",
        canonical_id,
        locale,
    )
    if "singular" not in preferred:
        raise fault("preferred.singular", "is required")

    alternates = forms.get("alternates", [])
    if not isinstance(alternates, list):
        raise fault(
            "alternates", f"must be an array of labels, not {_kind(alternates)}"
        )

    named_forms = [("preferred.singular", preferred["singular"])]
    if "plural" in preferred:
        named_forms.append(("preferred.plural", preferred["plural"]))
    named_forms += [
        (f"alternates[{index}]", alternate)
        for index, alternate in enumerate(alternates)
    ]
    for field, surface_form in named_forms:
        if not isinstance(surface_form, str):
            raise fault(field, f"must be a label, not {_kind(surface_form)}")
        if not surface_form:
            raise fault(field, "is empty; a surface form nobody can type is a bug")
        # Beyond the schema, whose minLength cannot tell a label from a blank
        # one (see docs/lexicon-semantic-checks.md).
        if not surface_form.strip():
            raise fault(
                field,
                f"is {surface_form!r}, which is only whitespace; that is not a "
                f"label a user can type",
            )
        # Beyond the schema, which bounds a surface form's length below but not
        # above (see docs/lexicon-semantic-checks.md). A form this long is not a
        # label a user types; left in, it would make matching pathologically
        # slow, so it is refused at load rather than at match time.
        if len(surface_form) > MAX_SURFACE_FORM_LENGTH:
            raise fault(
                field,
                f"is {len(surface_form)} characters long, which exceeds the "
                f"maximum surface-form length of {MAX_SURFACE_FORM_LENGTH}; a "
                f"label this long would make matching pathologically slow",
            )

    return SurfaceForms(
        preferred_singular=preferred["singular"],
        preferred_plural=preferred.get("plural"),
        alternates=tuple(alternates),
    )


def _reject_ambiguous_surface_forms(
    entities: dict[str, dict[str, SurfaceForms]],
) -> None:
    """Refuse a lexicon in which one word could resolve to two entities.

    Beyond the schema, which cannot see across entities (see
    docs/lexicon-semantic-checks.md). Determinism is a headline guarantee, and
    there is no defensible way to pick a winner here — so the ambiguity is
    refused at load time rather than resolved arbitrarily in production.
    """
    claimed: dict[tuple[str, str], tuple[str, str]] = {}
    for canonical_id, locales in entities.items():
        for locale, forms in locales.items():
            for field, surface_form in _named_forms(forms):
                key = (locale, surface_form.casefold())
                if key in claimed:
                    owner, owner_field = claimed[key]
                    raise _fault(
                        field,
                        f"claims the surface form {surface_form!r}, which entity "
                        f"{owner!r} already claims as {owner_field!r} in this "
                        f"locale; one word cannot resolve to two entities",
                        canonical_id=canonical_id,
                        locale=locale,
                    )
                claimed[key] = (canonical_id, field)


def _named_forms(forms: SurfaceForms) -> list[tuple[str, str]]:
    """Every surface form of one entity in one locale, paired with its field."""
    named = [("preferred.singular", forms.preferred_singular)]
    if forms.preferred_plural is not None:
        named.append(("preferred.plural", forms.preferred_plural))
    named += [
        (f"alternates[{index}]", alternate)
        for index, alternate in enumerate(forms.alternates)
    ]
    return named


def _fault(
    field: str,
    reason: str,
    *,
    canonical_id: str | None = None,
    locale: str | None = None,
) -> ValidationError:
    """One sentence naming whichever coordinates the fault has."""
    where = ""
    if canonical_id is not None:
        where = f"Entity {canonical_id!r}"
        if locale is not None:
            where += f", locale {locale!r}"
        where += ": "
    return ValidationError(
        f"{where}field {field!r} {reason}.",
        canonical_id=canonical_id,
        locale=locale,
        field=field,
    )


def _reject_unknown_keys(
    mapping: dict[str, Any],
    known: frozenset[str],
    where: str,
    canonical_id: str | None = None,
    locale: str | None = None,
) -> None:
    unknown = sorted(set(mapping) - known)
    if unknown:
        raise _fault(
            unknown[0],
            f"is not part of the lexicon format; {where} accepts "
            f"{', '.join(sorted(known))}",
            canonical_id=canonical_id,
            locale=locale,
        )


def _kind(value: Any) -> str:
    """The JSON name for what a value turned out to be, for error messages."""
    return {
        dict: "an object",
        list: "an array",
        str: "a string",
        bool: "a boolean",
        int: "a number",
        float: "a number",
        type(None): "null",
    }.get(type(value), f"a {type(value).__name__}")
