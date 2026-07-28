# ADR 0005 — entry metadata: several terms, one entity, with a discriminating filter

## Status

Accepted (2026-07-28)

## Context

A tenant's vocabulary is rarely one word per database entity. A German media company's users type "film", "filme", "spielfilm", "serie" and "serien", and every one of those is, to the backend, the same `product`. What distinguishes them is not *which* entity to query but *how to narrow it*: a movie is a `product` with `productType = Movie`, a series is a `product` with `productType = Series`.

The format as first shipped could not say this. Entities were keyed by canonical ID, so two of a tenant's terms could not both resolve to `product`, and an entity carried nothing but its per-locale surface forms. An author facing this had three bad options: invent canonical IDs (`movie`, `series`) that no backend queries, and let the consuming service maintain its own mapping back to `product`; collapse everything into one entity and lose the distinction; or hardcode the discrimination in application code — which is the practice lexiqr exists to remove.

The integrating developer felt the same gap from the other side. A match report said *which entity* was named but not the qualification the tenant's own word implied, so the jargon-to-filter half of the mapping leaked back into their service as a per-tenant lookup table.

This ADR records what was decided, and — more usefully — what was rejected. It refines ADR 0003's data shapes; it does not supersede ADR 0002 or ADR 0003, both of which continue to hold.

## Decision

- **An entry, not an entity.** The key an object sits under in `entities` is the **entry ID**. An entry may declare `canonicalId`, the entity a match resolves to, which **defaults to the entry ID** when omitted. Several entries may resolve to one canonical ID.

  *Rejected: hiding the target inside the metadata bag* under a magic key such as `_entity`. That restores convention-over-contract — the thing lexiqr exists to remove — and puts a field the library must read inside a bag the library promises never to interpret.

  *Rejected: nesting senses under an entity* (`entities.product.senses.movie`). This is the truest model of the domain, and it stays available: the same match report can be reached from the design chosen here without changing the public contract. It was rejected for now because it turns the entity object into a **shape union** that every loading, indexing and ambiguity-checking loop must branch on, for a gain no consumer can observe.

  Defaulting to the entry ID is what makes the change free for every lexicon already written: a document that never mentions a target means exactly what it always meant, and no author is made to name an entity twice.

- **A target must be a leaf.** A `canonicalId` naming an entry that itself resolves elsewhere is refused at load. Following the chain would invent a rule the format does not state; stopping at the first hop makes a match report an entity no backend queries. Documented in [lexicon-semantic-checks.md](../lexicon-semantic-checks.md) with the reason JSON Schema cannot express it.

- **The canonical-tier surface form is the entry ID, never the target.** A prompt naming "movie" outright still resolves; the literal word `product` is matchable only when an entry is named for it. Otherwise every entry sharing a target would claim the same canonical-tier form and the ambiguity check would refuse the lexicon for a reason internal to lexiqr. For an entry that resolves to itself the two are the same string, so nothing changes.

- **A bounded metadata value domain.** An entry may carry `metadata`: at most 16 keys matching the identifier grammar up to 64 characters, each value a string (1–128 characters), a number, a boolean, or a list of 1–16 unique strings.

  *Rejected: `null` as a value* — an absent key already means absent, so a null adds a second way to say nothing and a second case for every consumer to handle.

  *Rejected: nesting* — nested objects invite a query language (operators, conditions, precedence), which is a stated non-goal. A filter value is a scalar or a set of scalars.

  Every guarantee lexiqr makes is a bound. Results are immutable, hashable, and identical across runs; a bag of arbitrary depth and size would put all three at the mercy of a tenant's file.

- **Carry, never interpret.** lexiqr moves the bag from the lexicon to the match report and does nothing else with it. Metadata never influences which matches are returned, their score tiers, or their order. What `productType = Movie` means to a search backend stays in the consuming service, exactly as the vision's non-goal on filter building requires — which is why that non-goal is worded as *carries filter metadata but never builds or validates filters* rather than as silence about metadata.

- **The value type is its own module.** `lexiqr.metadata` owns the domain, the bounds, immutability, hashing, sorted iteration, and the canonical payload conversion, behind a small interface, and is testable with no lexicon, index or resolver constructed. It reports *what* is wrong and which key; the loader adds *where*, because only the loader knows.

- **The entry ID on a match is always a real string.** `EntityMatch.entry_id` equals the canonical ID for an entry that resolves to itself, rather than being optional and meaning "same as the canonical ID".

  *Rejected: an optional field.* It reads as cheaper and is not: serialization would have to emit a null or invent a value on read, and either breaks the exact round-trip guarantee — `deserialize_report(serialize_report(r)) == r` — that makes a stored report comparable to the one it was stored from.

  Non-optional forces `entry_id` **positionally ahead of `correction`**, reordering the match fields. That was free before the first release tag and impossible after it, which is the whole reason the reorder happened when it did.

- **Serialization always emits both keys.** `entry_id` as a string and `metadata` as an object, empty when the entry declares none. No conditional emission and no asymmetry between a report that used the feature and one that did not, so a consumer's parser never branches on whether a key exists. This broke every snapshot taken from an earlier build; the serialization module's shape promise binds **from the first release tag onward**, and says so.

- **The format is amended in place; there is no second schema version.** The published schema at the previous tag keeps resolving to the bytes it had; the amended schema is republished at the pending release tag with `$id`, the publication record, every `$schema` reference and the authoring guide's URL moved together, and the procedure written down in [RELEASING.md](../../RELEASING.md).

  *Rejected: a second schema version* with a dual-version loading path. It is the right answer for a published format and the wrong one here: nothing had shipped to PyPI and the only tag predated the current format, so a second version would have bought compatibility with a format no one was using, at the cost of a branch in the loader forever. **This justification is the pre-publication window and nothing else** — recorded so that the next format change, which will happen after publication, is not argued from this precedent.

- **Identifier validation is tightened.** Core validated no identifier grammar at all, which was looser than the published schema an author validates against offline. Both the entry key and the `canonicalId` value are now checked against the schema's pattern, so both sides of the ADR 0003 equivalence contract give the same verdict.

- **The identity component of every match-pass ordering is `(canonical ID, entry ID)`.** With several entries resolving to one entity, two candidates can tie on everything else, and the canonical ID alone stops being a total tiebreak. `lexiqr.ordering` owns that key and both ranking sites read it, so the invariant has one home and one test.

## Consequences

- Two entries may name one entity, and a consuming service builds a search filter directly from a match report — no per-tenant table on its side. That is the whole point.
- The permissiveness is deliberate where it is permissive: entries sharing a canonical ID need not agree on their metadata key set, since a more specific entry reasonably carries a more specific filter. Pinned by a test so it stays a decision.
- Two beyond-schema semantic checks join the documented divergence list: the chained target, and a whitespace-only metadata value. Both are refused for the same class of reason a whitespace-only surface form is.
- The match report grew two fields and reordered one. Positionally-constructed `EntityMatch` values, and snapshots of the canonical serialization, both had to change. Doing it before publication cost a fixture update; after publication it would have been a major version.
- The performance envelope now holds for a lexicon whose every entry declares a filter, which it does only because metadata is carried by shared reference rather than copied per hit. The benchmark fixture declares metadata everywhere so the envelope that is measured is the one adopters get.
- ADR 0003's data-shape sentence is refined, not contradicted: a lexicon document is a schema version, a default locale, and **entries** keyed by entry ID, each naming the entity it resolves to and optionally carrying metadata, with per-locale surface forms.
