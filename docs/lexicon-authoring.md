# Writing a lexicon

A lexicon is one JSON file: your tenant's mapping from the words your users
actually type to the canonical entities your backend knows about. You never
need to install lexiqr to write one, or to check that you wrote it correctly.

This page is for whoever maintains that file — a tenant admin, a
customer-success engineer, a localization specialist. It assumes no Python.

## The schema

The lexicon format is described by a published
[JSON Schema](https://json-schema.org/), at this URL:

```
https://raw.githubusercontent.com/bmeunier1974/lexiqr/v1.0.0/schema/lexicon.v1.schema.json
```

The version is in the path on purpose. That URL names a **tag**, and a tag
names one fixed commit — so the document it returns today is the document it
returns in two years. Your validation setup will not break under you when a
new schema version is published; a new version gets a new URL, and this one
keeps working.

> **Before the first release tag exists**, that URL does not resolve yet. Until
> then, use the copy in the repository at `schema/lexicon.v1.schema.json` — the
> bytes are identical, and `schema/published.json` records the tag the file is
> published at, checked by CI.

## Getting completion and inline errors while you write

Add a `$schema` key at the top of your lexicon. Most editors — VS Code, the
JetBrains IDEs, anything speaking the language server protocol — pick it up and
give you completion, hover documentation, and red squiggles as you type:

```json
{
  "$schema": "https://raw.githubusercontent.com/bmeunier1974/lexiqr/v1.0.0/schema/lexicon.v1.schema.json",
  "schemaVersion": "1",
  "defaultLocale": "de-DE",
  "entities": {
    "product": {
      "locales": {
        "de-DE": {
          "preferred": { "singular": "flooff", "plural": "flooffs" },
          "alternates": ["artikel", "ware"]
        }
      }
    }
  }
}
```

`examples/flooff.lexicon.json` in this repository is a complete working example
with the reference already in place.

## Several words, one entity, and the filter that tells them apart

Your users rarely have one word per thing in your database. A German media
tenant's users type "film", "filme", "spielfilm", "serie" and "serien" — and to
the backend every one of those is the same `product`. What separates them is not
*which* entity to query but *how to narrow it*: a movie is a `product` with
`productType = Movie`, a series is a `product` with `productType = Series`.

You say that with two **entries** resolving to one entity, each carrying the
filter that discriminates it:

```json
{
  "schemaVersion": "1",
  "defaultLocale": "de-DE",
  "entities": {
    "movie": {
      "canonicalId": "product",
      "metadata": { "productType": "Movie", "genre": ["drama", "thriller"] },
      "locales": {
        "de-DE": {
          "preferred": { "singular": "film", "plural": "filme" },
          "alternates": ["spielfilm"]
        },
        "en-GB": { "preferred": { "singular": "movie", "plural": "movies" } }
      }
    },
    "series": {
      "canonicalId": "product",
      "metadata": { "productType": "Series", "episodic": true },
      "locales": {
        "de-DE": { "preferred": { "singular": "serie", "plural": "serien" } },
        "en-GB": { "preferred": { "singular": "series" } }
      }
    }
  }
}
```

The complete file is
`schema/fixtures/valid/medien-shared-entity.lexicon.json` in this repository.

Three things to know about it:

**The key is the entry, `canonicalId` is the entity.** `movie` and `series` are
*entry* names — yours, for your own use. `product` is what your backend queries,
and it is what every match reports. Nothing forces you to invent entities your
database does not have.

**Omit `canonicalId` and the entry *is* the entity.** Every lexicon on this page
above this section omits it, and means exactly what it always meant: one word per
entity, entry name and canonical ID the same string. You only reach for the field
when you have a second word for the same thing.

Two rules go with it. Two entries may resolve to the same entity, but a
`canonicalId` may not point at an entry that itself resolves somewhere else — a
target has to be an entity, not another entry. And two entries still may not
claim the same word in the same locale: which filter would apply is unanswerable,
so the file is refused with a message naming both entries.

**`metadata` is yours; lexiqr never interprets it.** It carries your bag from the
file to the match report, verbatim, and does nothing else with it — no filter
building, no validation of what the keys mean, and no effect on which matches come
back or in what order. Turning `productType = Movie` into a query is your
service's job.

A filter holds up to 16 keys. Each key is letters, digits, `_`, `.` or `-`, up to
64 characters. Each value is one of:

| Value | Example | Notes |
| --- | --- | --- |
| a string | `"Movie"` | 1–128 characters, and not just whitespace |
| a number | `12`, `7.5` | |
| a boolean | `true` | |
| a list of strings | `["drama", "thriller"]` | 1–16 entries, no repeats — for a genuinely multi-valued filter like `genre` |

There is deliberately no `null` (leave the key out instead) and no nesting — a
value is a scalar or a set of scalars, because a filter language is not something
lexiqr has.

Entries resolving to the same entity do **not** have to carry the same keys. A
more specific entry reasonably carries a more specific filter.

### Confirming it works

`lexiqr try` shows you the entity, the entry that answered, and the filter it
carried:

```bash
lexiqr try medien.lexicon.json --locale de-DE "wo sind die filme"
```

```text
prompt: "wo sind die [filme]"
resolved via: de-DE
1 match:

  [1] product ← "filme"
      tier: preferred   locale: de-DE   text: "filme"
      entry: movie
      filter: genre=drama|thriller, productType=Movie
```

The `entry:` line appears only when the entry resolves to a different entity, and
the `filter:` line only when the entry carries metadata — so a lexicon that uses
neither reads exactly as it did before these existed. A misspelling resolves the
same way and carries the same filter, with a `correction:` line added.

## Checking a file before you ship it

Any standard JSON Schema validator will do — nothing lexiqr-specific is
involved. Two convenient ones:

```bash
# check-jsonschema (pipx install check-jsonschema)
check-jsonschema --schemafile \
  https://raw.githubusercontent.com/bmeunier1974/lexiqr/v1.0.0/schema/lexicon.v1.schema.json \
  my-tenant.lexicon.json

# ajv-cli (npm install -g ajv-cli ajv-formats)
ajv validate --spec=draft2020 \
  -s lexicon.v1.schema.json -d my-tenant.lexicon.json
```

A file that passes is a file lexiqr will load. That is a guarantee, not a
hope — see [ADR 0003](adr/0003-core-schema-contract.md), and the test suite
runs every fixture through both validators on every pull request to keep it
true.

## Checking a file with lexiqr itself

If you install lexiqr, it ships a command line that needs no Python. It loads
through the same code path the library does, so a file the CLI accepts is a file
the library loads — and when a file is wrong, the CLI shows you the same error
the library would raise, naming the entity, the locale, and the field.

```bash
pip install lexiqr

# Is my file valid? (the same errors the library raises at load time)
lexiqr validate my-tenant.lexicon.json

# What does a real customer phrasing resolve to?
lexiqr try my-tenant.lexicon.json --locale de-DE "wo ist flooff"
```

`lexiqr validate <lexicon>` takes one argument, the **lexicon** file to check.
`lexiqr try <lexicon> --locale <locale> "<prompt>"` resolves a **prompt**,
written in a **locale** (a BCP 47 tag), against the lexicon and prints the whole
match report: every match with its canonical ID, the surface form that matched,
the span marked in your prompt, the score tier, the locale that actually
answered, any correction a fuzzy match applied, and — when the entry that
answered resolves to a different entity, or carries metadata — the entry and its
filter. Run either command with `--help` to see its arguments.

### Exit codes

Both commands exit with a code a script can branch on, so you can wire
`lexiqr validate` into a pre-commit hook or CI job, and `lexiqr try` into a
regression check over a list of known prompts, without lexiqr knowing anything
about your pipeline. Results go to stdout; every diagnostic and error goes to
stderr, so you can pipe or capture just the part you need.

| Exit code | `validate` | `try` |
|-----------|------------|-------|
| `0` | the lexicon is valid | at least one match was found |
| `1` | the lexicon is invalid — core rejected it | the lexicon is invalid |
| `2` | a usage error: a missing or wrong argument | a usage error |
| `3` | a CLI-level failure: the file is missing, unreadable, or not valid JSON | the same CLI-level failure |
| `4` | — | no match: the lexicon loaded, but the prompt resolved to nothing |

The distinctions are deliberate. A **load failure** — `1` for an invalid
lexicon, `3` for a missing or malformed file — is always distinguishable from
`try`'s **no match** (`4`), so a regression script can tell "your lexicon is
broken" from "this prompt simply did not resolve". And a CLI-level failure (`3`)
is distinguishable from an invalid lexicon (`1`), so "your path is wrong" never
looks like "your lexicon is wrong". A usage error keeps code `2`, the
conventional argument-parser code, and prints a usage message rather than a
stack trace.

## The one exception

There is a short list of problems the schema cannot express — an ambiguous
lexicon where two entities claim the same word, for instance. lexiqr rejects
those even though the schema accepts them, and every one of them is enumerated
in [docs/lexicon-semantic-checks.md](lexicon-semantic-checks.md) with the
reason it cannot live in the schema.

If your file validates offline but lexiqr still refuses it, the error names the
entity, the locale, and the field, and the cause will be on that list.
