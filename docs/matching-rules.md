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

Matches that do not overlap are all kept. A prompt mentioning an entity twice
reports both spans; a prompt naming three entities reports all three.

## 7. The report is ordered by position

The final match list is sorted by span start in the original prompt — reading
order, not confidence order. A `canonical`-tier match early in the sentence
comes before a `preferred`-tier match later in it. Sort by `score_tier`
yourself if you want them ranked by confidence.

---

## What determinism does and does not cover

Guaranteed: the same lexicon document and the same prompt produce an identical
match report — same matches, same spans, same tiers, same order — across runs,
processes, machines, and supported Python versions. Rebuilding the resolver from
the same document changes nothing.

Not guaranteed, and not part of the public contract: how the scan is
implemented, how the index is laid out, or how many intermediate candidates were
considered on the way to the answer.
