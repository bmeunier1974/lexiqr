"""Loading a lexicon document into core's internal model.

One entry point in, one validated `Lexicon` — or a `ValidationError` naming
exactly where the document is wrong (ADR 0002, ADR 0003). Callers hand over a
JSON file path or a parsed dict and get back something core can trust; nothing
downstream of here re-checks the data.

What the document keys under `entities` is read as an **entry**: a named set of
surface forms plus the entity it resolves to. The two are the same identifier
unless the entry says otherwise, which is why a lexicon written before entries
existed means exactly what it always meant.

Faults are reported with whatever coordinates they have. A bad `entities`
belongs to the document, a bad locale key belongs to an entry, a bad surface
form belongs to an entry *and* a locale — and the coordinates a fault does not
have stay `None` rather than being invented.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lexiqr.errors import MalformedDocumentError, ValidationError, kind
from lexiqr.locale import is_well_formed
from lexiqr.metadata import EMPTY, Metadata, MetadataFault

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

#: What an identifier may be spelled with — the published schema's
#: `$defs/canonicalId`, mirrored here so both sides of the ADR 0003 contract give
#: the same verdict. Both an entry ID and the `canonicalId` it resolves to are
#: identifiers, and both are checked: core used to accept any string as a key,
#: which was looser than the schema an author validates against offline.
_IDENTIFIER = re.compile(r"^[A-Za-z0-9_.-]+$")

#: Keys the v1 format defines, mirroring the schema's `additionalProperties`
#: bans. A key outside these is a typo, and a typo silently ignored is a
#: surface form the tenant believes is live and isn't.
_DOCUMENT_KEYS = frozenset({"$schema", "schemaVersion", "defaultLocale", "entities"})
_ENTITY_KEYS = frozenset({"canonicalId", "locales", "metadata"})
_SURFACE_FORM_KEYS = frozenset({"preferred", "alternates"})
_PREFERRED_KEYS = frozenset({"singular", "plural"})


@dataclass(frozen=True)
class SurfaceForms:
    """The surface forms of one entity in one locale."""

    preferred_singular: str
    preferred_plural: str | None = None
    alternates: tuple[str, ...] = ()


@dataclass(frozen=True)
class Entry:
    """One named set of surface forms, and the entity it resolves to.

    The key an entity object sits under in the document is the **entry ID**: the
    tenant's name for this way of naming the thing. The **canonical ID** is what a
    match resolves to — the entity a backend actually queries — and it defaults to
    the entry ID, so a lexicon that never mentions a target says exactly what it
    always said. Several entries may resolve to one canonical ID: "movie" and
    "series" can both be `product`.
    """

    entry_id: str
    canonical_id: str
    locales: dict[str, SurfaceForms]
    #: The filter that tells this entry's entity from another entry's. Empty
    #: rather than absent when the entry declares none, so nothing downstream
    #: needs a guard.
    metadata: Metadata = EMPTY


@dataclass(frozen=True)
class Lexicon:
    """A tenant's jargon-to-entity mapping, as core sees it."""

    schema_version: str
    default_locale: str
    entries: dict[str, Entry]

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
        if not isinstance(default_locale, str) or not is_well_formed(default_locale):
            raise _fault(
                "defaultLocale",
                f"is {default_locale!r}, which is not a well-formed locale tag "
                f"(expected BCP 47, e.g. 'de-DE')",
            )

        entities = document.get("entities")
        if not isinstance(entities, dict):
            raise _fault(
                "entities",
                f"must be an object keyed by entry ID, not {kind(entities)}",
            )
        if not entities:
            raise _fault(
                "entities", "is empty; a lexicon with no entities resolves nothing"
            )

        parsed = {
            entry_id: _entry(entity, entry_id) for entry_id, entity in entities.items()
        }
        _reject_chained_targets(parsed)
        _reject_ambiguous_surface_forms(parsed)
        return cls(
            schema_version=SCHEMA_VERSION,
            default_locale=default_locale,
            entries=parsed,
        )

    @classmethod
    def from_file(cls, path: str | Path) -> Lexicon:
        """Read `path`, parse it, and validate what it holds — once, here.

        This is the one place lexiqr turns a file into a lexicon, so it is also
        the one place the wording for "that file is not JSON" is written. A
        caller that reads and parses the file itself only to hand the result to
        `from_dict` would be phrasing that failure a second time, and the two
        phrasings would drift.

        The two ways this fails are kept apart by type: an unreadable path is
        the operating system's `OSError`, reported in its own words, while a
        file that is not JSON is a `MalformedDocumentError`.
        """
        text = Path(path).read_text(encoding="utf-8")
        try:
            document = json.loads(text)
        except json.JSONDecodeError as broken:
            raise MalformedDocumentError(
                f"{path} is not valid JSON: {broken.msg} "
                f"(line {broken.lineno}, column {broken.colno})."
            ) from broken
        return cls.from_dict(document)


def _entry(entity: Any, entry_id: str) -> Entry:
    """One entity object, read as the entry it is: a target and its forms."""
    if not isinstance(entity, dict):
        raise _fault(
            "entities",
            f"maps {entry_id!r} to {kind(entity)}, not an entity object",
            canonical_id=entry_id,
        )
    if not _IDENTIFIER.fullmatch(entry_id):
        raise _fault(
            "entities",
            f"has key {entry_id!r}, which is not a well-formed identifier "
            f"(letters, digits, '_', '.' and '-')",
        )
    _reject_unknown_keys(entity, _ENTITY_KEYS, f"entity {entry_id!r}", entry_id)

    # Omitted means "this entry resolves to itself", which is what every lexicon
    # written before the field existed says, so no author names an entity twice.
    canonical_id = entity.get("canonicalId", entry_id)
    if not isinstance(canonical_id, str) or not _IDENTIFIER.fullmatch(canonical_id):
        raise _fault(
            "canonicalId",
            f"is {canonical_id!r}, which is not a well-formed identifier "
            f"(letters, digits, '_', '.' and '-')",
            canonical_id=entry_id,
        )

    return Entry(
        entry_id=entry_id,
        canonical_id=canonical_id,
        locales=_locales(entity, entry_id),
        metadata=_metadata(entity.get("metadata"), entry_id),
    )


def _metadata(declared: Any, entry_id: str) -> Metadata:
    """The entry's filter, with the coordinates only this module knows added.

    `lexiqr.metadata` owns what a filter may be; the loader owns where in the
    document a bad one was found. The two meet here, so the message reads with the
    same voice as every other validation error.
    """
    try:
        return Metadata.of(declared)
    except MetadataFault as fault:
        raise _fault(fault.field, fault.reason, canonical_id=entry_id) from fault


def _locales(entity: dict[str, Any], canonical_id: str) -> dict[str, SurfaceForms]:
    locales = entity.get("locales")
    if not isinstance(locales, dict):
        raise _fault(
            "locales",
            f"must be an object keyed by locale tag, not {kind(locales)}",
            canonical_id=canonical_id,
        )
    if not locales:
        raise _fault(
            "locales",
            "is empty; an entity with no locales can never be matched",
            canonical_id=canonical_id,
        )

    for locale in locales:
        if not is_well_formed(locale):
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
        raise fault("locales", f"maps {locale!r} to {kind(forms)}, not surface forms")
    _reject_unknown_keys(
        forms,
        _SURFACE_FORM_KEYS,
        f"entity {canonical_id!r}, locale {locale!r}",
        canonical_id,
        locale,
    )

    preferred = forms.get("preferred")
    if not isinstance(preferred, dict):
        raise fault("preferred", f"must be an object, not {kind(preferred)}")
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
        raise fault("alternates", f"must be an array of labels, not {kind(alternates)}")

    named_forms = [("preferred.singular", preferred["singular"])]
    if "plural" in preferred:
        named_forms.append(("preferred.plural", preferred["plural"]))
    named_forms += [
        (f"alternates[{index}]", alternate)
        for index, alternate in enumerate(alternates)
    ]
    for field, surface_form in named_forms:
        if not isinstance(surface_form, str):
            raise fault(field, f"must be a label, not {kind(surface_form)}")
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


def _reject_chained_targets(entries: dict[str, Entry]) -> None:
    """Refuse a lexicon whose entity resolves through another entry.

    Beyond the schema, which validates each entity object on its own and so
    cannot compare a value in one against the key of another (see
    docs/lexicon-semantic-checks.md).

    A target must be a **leaf**. `feature_film` → `movie` → `product` has no
    honest reading: following the chain invents a rule the format does not state,
    and stopping at the first hop leaves a match reporting `movie`, which is not
    an entity any backend queries. Pointing at an entry that resolves to *itself*
    is fine — that entry is the entity.
    """
    for entry_id, entry in entries.items():
        target = entries.get(entry.canonical_id)
        if target is None or target.canonical_id == target.entry_id:
            continue
        raise _fault(
            "canonicalId",
            f"resolves to {entry.canonical_id!r}, which is itself an entry "
            f"resolving to {target.canonical_id!r}; a target must be an entity, "
            f"not another entry — name {target.canonical_id!r} directly",
            canonical_id=entry_id,
        )


def _reject_ambiguous_surface_forms(
    entries: dict[str, Entry],
) -> None:
    """Refuse a lexicon in which one word could resolve to two entries.

    Beyond the schema, which cannot see across entities (see
    docs/lexicon-semantic-checks.md). Determinism is a headline guarantee, and
    there is no defensible way to pick a winner here — so the ambiguity is
    refused at load time rather than resolved arbitrarily in production.

    The rule keys on locale and folded surface form, which is why it needs no
    change now that several entries may share a target: it already refuses both
    bad cases. Two entries with *different* metadata claiming one word leaves
    which filter applies unanswerable; two with the same target and the same
    metadata is a redundant declaration. What did change is the wording — with
    two entries resolving to one entity, naming only the entity says nothing
    about which pair collided.
    """
    claimed: dict[tuple[str, str], tuple[Entry, str]] = {}
    for entry in entries.values():
        for locale, forms in entry.locales.items():
            for field, surface_form in _named_forms(forms):
                key = (locale, surface_form.casefold())
                if key in claimed:
                    owner, owner_field = claimed[key]
                    raise _fault(
                        field,
                        f"claims the surface form {surface_form!r}"
                        f"{_resolving(entry)}, which {_names(owner)} already "
                        f"claims as {owner_field!r} in this locale; one word "
                        f"cannot resolve to two entries",
                        canonical_id=entry.entry_id,
                        locale=locale,
                    )
                claimed[key] = (entry, field)


def _names(entry: Entry) -> str:
    """How an error refers to another entry: its name, and what it resolves to.

    The target is spelled out only when it differs from the entry ID. Repeating
    the same identifier twice would make every ambiguity error in every lexicon
    that never uses the feature read as though something more complicated were
    going on.
    """
    if entry.canonical_id == entry.entry_id:
        return f"entry {entry.entry_id!r}"
    return f"entry {entry.entry_id!r} (resolving to {entry.canonical_id!r})"


def _resolving(entry: Entry) -> str:
    """The target of the entry a fault is reported against, when it has its own.

    The fault's coordinates already name that entry, so only the entity it means
    is missing — and only when the two differ.
    """
    if entry.canonical_id == entry.entry_id:
        return ""
    return f" for {entry.canonical_id!r}"


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
