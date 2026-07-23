# Semantic checks: where core is stricter than the schema

Almost everything lexiqr rejects, the [published JSON Schema](../schema/lexicon.v1.schema.json)
rejects too. That is the point of [ADR 0003](adr/0003-core-schema-contract.md):
**a lexicon file that passes the published schema loads in core**, so validating
offline with standard tooling is a trustworthy preflight rather than an
approximation.

ADR 0003 licenses one exception. Core may enforce checks that are *stricter*
than the schema — never looser — and every such check must be written down.
This is that document. It is the complete list; a check that is not here is
drift, and the test suite fails if a semantic fixture exists without an entry.

Each check below is paired with a fixture in `schema/fixtures/semantic/`. Every
one of those files passes the published schema and is still rejected by core —
that is what makes it a divergence rather than an ordinary structural error.

---

## 1. One surface form may not be claimed by two entities in the same locale

**Fixture:** `duplicate-surface-form-across-entities.lexicon.json`

Two entities in one locale both claiming the word "flooff" makes resolution
ambiguous: the prompt "wo ist flooff" would have two equally good answers.

*Why the schema cannot express it.* JSON Schema validates each entity against
`$defs/entity` independently. It has no way to compare a value inside one
entity with a value inside another, so a collision is invisible to it.

*Why core rejects rather than picks a winner.* Determinism is a headline
guarantee — the same lexicon and prompt must give the same result on every run
and platform. Any tie-break here (declaration order, alphabetical canonical ID)
would be arbitrary and would silently hide a lexicon the tenant almost
certainly did not mean to write. Refusing at load time makes the ambiguity the
lexicon author's to resolve, which is where it belongs.

## 2. One entity may not declare the same surface form twice in one locale

**Fixture:** `duplicate-surface-form-within-one-entity.lexicon.json`

An `alternates` entry repeating that locale's `preferred.singular` (or
`preferred.plural`) is a redundant declaration.

*Why the schema cannot express it.* `uniqueItems` covers duplicates *within*
the `alternates` array, but nothing in JSON Schema compares an array element
against a sibling object's property.

*The stated decision: rejected, not de-duplicated.* A repeated form would match
the same span twice at two different score tiers, so the match report would
carry a duplicate entry whose tier depended on which declaration was read
first. Silently dropping the repeat would hide the mistake; rejecting it tells
the author their lexicon says something they did not mean.

## 3. A surface form may not be only whitespace

**Fixture:** `blank-surface-form.lexicon.json`

`"   "` is a string of length three, so `minLength: 1` accepts it.

*Why the schema cannot express it.* It could, with a pattern — but the schema
deliberately keeps `$defs/surfaceForm` a plain non-empty string so that authors
writing forms in any script are not tripped by a regex built around Latin
assumptions. Core carries the check instead.

*Why core rejects.* A whitespace-only form is not a label any user can type,
and it cannot participate in the whole-word matching lexiqr does. It is a data
entry slip, and reporting it costs the author far less than discovering later
that an entity never matches.

---

## For lexicon authors

If offline validation passes and lexiqr still rejects your file, the error
message names the entity, locale, and field — and the reason will be one of the
three above. Nothing else in lexiqr rejects a schema-valid document.
