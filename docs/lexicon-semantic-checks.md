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

## 4. A surface form may not exceed the maximum length

**Fixture:** `pathological-surface-form.lexicon.json`

`$defs/surfaceForm` sets `minLength: 1` but no upper bound, so a 200-character
"label" passes the schema. Core caps a surface form at **128 code points**.

*Why the schema cannot express it.* The schema *could* add a `maxLength`, and
this is the one check that is a candidate to migrate there later. It stays in
core for now because the bound exists for a matching-cost reason, not a document
well-formedness one: the number belongs next to the matcher it protects, and
pinning it here keeps the offline schema free of a performance constant that
core owns. Moving it into the published schema would be a deliberate, recorded
decision, not a default.

*Why core rejects.* A surface form is matched as a whole word and compared under
edit distance, so its length multiplies the cost of every scan. A form far
longer than any real label is not data a tenant meant to write — it is what a
pathological lexicon looks like — and left unbounded it would make matching
pathologically slow. Rejecting it at load turns a request-path hang into a
validation-time error the author can act on, which is where a bad lexicon should
fail.

## 5. A `canonicalId` may not point at an entry that resolves somewhere else

**Fixture:** `chained-canonical-id-target.lexicon.json`

An entry may name the entity it resolves to, and several entries may name the
same one. What it may not name is another entry that itself resolves onward:
`feature_film` → `movie` → `product`. A target must be a **leaf** — an entity, or
an entry that resolves to itself.

*Why the schema cannot express it.* JSON Schema validates each entity object
against `$defs/entity` on its own. Deciding whether a `canonicalId` names a leaf
means reading the *other* entity under that key and looking at its `canonicalId` —
a comparison across siblings, which is exactly what JSON Schema cannot do.

*Why core rejects rather than following the chain.* Neither reading is honest.
Resolving transitively invents a rule the format does not state, and every author
would then have to know how deep it goes. Stopping at the first hop makes the
match report `movie` — an entity no backend queries — which is the very failure
the entry model exists to remove. Refusing at load time puts the one-line fix
where it belongs: name `product` directly.

## 6. A metadata value may not be only whitespace

**Fixture:** `blank-metadata-value.lexicon.json`

`"   "` is a string of length three, so the `metadata` subschema's `minLength: 1`
accepts it — exactly as it accepts a blank surface form (check 3).

*Why the schema cannot express it.* It could, with a pattern, and it is left out
for the same reason: a metadata value is tenant-authored text in whatever script
the tenant writes, and a regex built around Latin assumptions would refuse
legitimate values. Core carries the check instead.

*Why core rejects.* Metadata is carried onto every match the entry produces and
read by a consuming service building a query. A value that is only spaces is not
something a backend can act on, but it is not nothing either: it becomes a live
filter that silently narrows every query, and the symptom is a search that quietly
returns less than it should. That is far more expensive to find later than at load
time.

---

## For lexicon authors

If offline validation passes and lexiqr still rejects your file, the error
message names the entity, locale, and field — and the reason will be one of the
six above. Nothing else in lexiqr rejects a schema-valid document.
