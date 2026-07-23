# Matching rules: what lexiqr does to your prompt, and why

lexiqr promises the same prompt and the same lexicon give the same match report
on every run, machine, and Python version. That promise makes the rules below
part of the public API: you can cache a report, snapshot-test it, and reason
about it, which means these rules cannot change without a semver bump any more
than a function signature can.

This is the complete list. Nothing else about matching is guaranteed.

---

## 1. Your prompt is folded before it is searched — but never returned folded

Matching compares a folded form of your prompt against a folded form of each
surface form the lexicon declares. Folding is what makes "Épisodes" and
"episodes" the same word.

**For Latin-script locales**, folding is: NFKD decomposition, then combining
marks are discarded, then casefolding. A user typing "épisodes" matches a
lexicon that says "episodes", and a tenant who wrote "épisodes" is found in a
prompt typed without the accent. Both directions work, because both sides are
folded the same way.

**For Arabic locales** (`ar`, any region), folding is casefolding only. Arabic
diacritics are not discarded, and `أ` is not reduced to `ا`. A haraka is not a
French acute: dropping it does not fold Arabic, it corrupts it, and reducing
`أ` to `ا` would invent matches between words that are simply different. The
guarantee for Arabic in v1 is that your text is left alone, not that matching
is tuned for Arabic morphology.

The prompt in the match report is always the exact string you passed in.

## 2. Spans index the prompt you typed, not the folded text

Every `span` in a match is a pair of character offsets into `MatchReport.prompt`.
`report.prompt[start:end]` is always the text that matched, so you can highlight
it or slice it without recomputing anything.

This is not free, and it is the reason folding is confined to one module.
Folding does not preserve length: `ß` casefolds to `ss`, and a precomposed `é`
decomposes to two characters before losing one. Offsets computed against the
folded text drift from the original by an amount that varies along the string.
lexiqr carries an offset map alongside the folded text and translates every hit
back through it once, at the boundary where the report is built.

So a match on "Straße" in "die Straße und die Gasse" reports the span of
"Straße" — six characters — not the seven its folded form occupies.

## 3. A surface form only matches as a whole word

"bill" does not match inside "billing". A form matches only where it is not
adjacent to another word character on either side.

## 4. Three tiers, in this order: preferred, alternate, canonical

Every match carries a `score_tier` saying how it was found:

| Tier | What matched | What it means for you as a lexicon author |
| --- | --- | --- |
| `preferred` | `preferred.singular` or `preferred.plural` | Your tenant's own word for the thing. Plurals are first-class: "flooffs" scores exactly as well as "flooff". |
| `alternate` | an entry in `alternates` | A secondary synonym you wanted matched without promoting it. |
| `canonical` | the entity's canonical ID | A prompt naming the entity outright ("count product rows") still resolves, at the lowest confidence. |

If an entity's canonical ID reads the same as one of its own labels, that is one
surface form declared once, at its best tier — not two competing candidates.

## 5. Only the locale you asked for is searched

`transform(prompt, locale)` searches the surface forms that `locale` declares
and nothing else. A German form never matches an English prompt. If the lexicon
declares nothing for that locale, you get an empty match list — an ordinary
result, not an error. (The fallback chain that consults related locales is a
later plan; today `matched_locale` always equals the locale you passed.)

## 6. When two forms claim the same text, exactly one wins

The scan is deliberately greedy: it finds "support ticket" *and* the "ticket"
inside it, because it cannot know which you meant. Overlapping matches are then
resolved by these rules, applied in order until one of them decides:

1. **The longest span wins.** A tenant who wrote a precise multi-word label
   meant that label, not the shorter ones it contains. "support ticket" beats
   "ticket".
2. **Then the better score tier wins** — preferred over alternate over canonical.
3. **Then the earliest start wins.**
4. **Then the lower canonical ID wins**, compared as text.

Rules 1–3 encode a judgement about what a lexicon author meant. Rule 4 does not:
it exists so that a case with nothing left to distinguish it still resolves the
same way on every machine, rather than following whatever order the scan
happened to produce.

Rule 4 is rarely reached, because a lexicon in which two entities claim the same
surface form in one locale is [refused at load time](lexicon-semantic-checks.md).
That check compares casefolded text, so forms differing only by accent —
`épisode` and `episode` in two different entities — pass it and then collide
once folded. Rule 4 is what settles those.

These four rules order matches of the **same kind**. When an exact match and a
fuzzy one (§8) claim overlapping text, kind is asked first and the exact match
always wins — whatever the spans. A word you spelled correctly is never
displaced by a guess about one you didn't.

Matches that do not overlap are all kept. A prompt mentioning an entity twice
reports both spans; a prompt naming three entities reports all three.

## 7. The report is ordered by position

The final match list is sorted by span start in the original prompt — reading
order, not confidence order. A `canonical`-tier match early in the sentence
comes before a `preferred`-tier match later in it. Sort by `score_tier`
yourself if you want them ranked by confidence.

## 8. Typo tolerance: a second, fuzzy pass over what is left

Matching runs in **two passes**. Everything above is the first pass — the exact
scan — and it runs to completion first. A second, *fuzzy* pass then looks only
at the words the exact scan left **uncovered**, never at text an exact match
already claimed, and asks whether any of them is a near-miss of a declared
surface form. Tolerance never rewrites a match you could already trust, and
keeping the fuzzy pass strictly second — over the residue alone — is why it does
not slow down prompts the exact scan already resolved. Where the two passes ever
claim overlapping text, an exact hit **outranks** the fuzzy one outright (§6).

Everything in this section is public, semver-governed behaviour, for the same
reason the rules above are: determinism makes it observable, so you can predict
a correction without running the matcher and rely on it not changing under you
without a semver bump.

### The edit budget scales with the length of the surface form

How far a word may stray and still resolve depends on how much evidence it
carries. A three-letter jargon term gets no tolerance at all — otherwise it
would collide with every other short word in your prompt, and you could not
explain why "cat" resolved to `product`. Longer forms, which carry more signal,
tolerate more.

| Surface-form length | Edit budget |
| --- | --- |
| 3 characters or fewer | none — exact match only |
| 4–5 characters | 1 edit |
| 6 or more characters | 2 edits |

An edit is an inserted, deleted, or substituted character, or a **transposition**
of two adjacent characters — which counts as **one** edit, not two, because that
is how people actually mistype ("flooff" → "floff").

### A candidate must also be similar enough

The budget is a ceiling on distance, not the whole test. On top of it, a
candidate must clear a fixed **similarity threshold** — it must be both within
budget *and* similar enough — so the library never reaches for a wildly
different word just because the edit count happened to fit. A typo that exceeds
either bound simply returns no match: lexiqr fails quietly rather than
confidently. The budget and the threshold are fixed in v1; see *What tolerance
is not*, below.

### Ranking is total, so an ambiguous typo resolves the same way every time

When more than one surface form is a legal correction of the same word, they are
ranked by a totally ordered rule, applied in order until one decides:

1. **Higher similarity** wins.
2. **Then lower edit distance.**
3. **Then the better score tier** — preferred over alternate over canonical.
4. **Then the earliest start position**, which orders the matches the pass emits.

No tie falls through to iteration order: two forms that are otherwise identical
under these rules are settled the same way — by the lower canonical ID, as in
rule 6.4 — on every run, machine, and Python version.

### Phrases tolerate the same errors, including swapped words

A multi-word surface form is recovered from adjacent words in the residue, so a
two-word label survives a misspelling of one of its words, and survives its two
words being typed in the **swapped** order. "support tickte" and "ticket
support" both resolve to a `support ticket` entity, within the same budget and
threshold that single words obey.

### Fuzzy matches carry a correction; exact matches do not

Every fuzzy match populates `correction` with what you actually typed, while its
`surface_form` names the declared form it resolved to — so you can always show a
user, or a support ticket, that "floof" was read as "flooff". Its `span`,
`score_tier`, `canonical_id`, and `matched_locale` mean exactly what they do on
an exact match, and its span indexes your original prompt, so
`report.prompt[start:end]` is the misspelling as you typed it. An exact match
leaves `correction` as `None`; a correction present *is* the signal that
tolerance was applied.

### Turning tolerance off

The `fuzzy` keyword — accepted by `EntityResolver(...)`, `EntityResolver.from_file`,
and `EntityResolver.from_dict` — defaults to `True`, so typo tolerance works
with no configuration. Passing `fuzzy=False` returns the resolver to exact-only
behaviour: the fuzzy pass is skipped entirely rather than run and filtered, so
exact-only mode is also the fast mode, and no match in any report it produces
carries a correction. The keyword is public, semver-governed API.

### What tolerance is not

lexiqr does no **phonetic** (soundex-style) matching and no **semantic** or
embedding-based similarity — those are deliberate non-goals, not gaps to be
filled later. And there are no per-tenant tuning knobs beyond the on/off switch:
the edit budgets, the similarity threshold, and the scorer are fixed in v1. The
only fuzzy configuration is whether the pass runs at all.

---

## What determinism does and does not cover

Guaranteed: the same lexicon document and the same prompt produce an identical
match report — same matches, same spans, same tiers, same order — across runs,
processes, machines, and supported Python versions. Rebuilding the resolver from
the same document changes nothing.

Not guaranteed, and not part of the public contract: how the scan is
implemented, how the index is laid out, or how many intermediate candidates were
considered on the way to the answer.
