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
https://raw.githubusercontent.com/bmeunier1974/lexiqr/v0.0.1/schema/lexicon.v1.schema.json
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
  "$schema": "https://raw.githubusercontent.com/bmeunier1974/lexiqr/v0.0.1/schema/lexicon.v1.schema.json",
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

## Checking a file before you ship it

Any standard JSON Schema validator will do — nothing lexiqr-specific is
involved. Two convenient ones:

```bash
# check-jsonschema (pipx install check-jsonschema)
check-jsonschema --schemafile \
  https://raw.githubusercontent.com/bmeunier1974/lexiqr/v0.0.1/schema/lexicon.v1.schema.json \
  my-tenant.lexicon.json

# ajv-cli (npm install -g ajv-cli ajv-formats)
ajv validate --spec=draft2020 \
  -s lexicon.v1.schema.json -d my-tenant.lexicon.json
```

A file that passes is a file lexiqr will load. That is a guarantee, not a
hope — see [ADR 0003](adr/0003-core-schema-contract.md), and the test suite
runs every fixture through both validators on every pull request to keep it
true.

## The one exception

There is a short list of problems the schema cannot express — an ambiguous
lexicon where two entities claim the same word, for instance. lexiqr rejects
those even though the schema accepts them, and every one of them is enumerated
in [docs/lexicon-semantic-checks.md](lexicon-semantic-checks.md) with the
reason it cannot live in the schema.

If your file validates offline but lexiqr still refuses it, the error names the
entity, the locale, and the field, and the cause will be on that list.
