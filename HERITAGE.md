# Heritage and provenance

lexiqr's deterministic core descends from a design first worked out on a private
repository's branch 735. This note records, plainly and permanently, how that
lineage relates to the code published here — so anyone asking about provenance
gets the same answer the maintainer would give, without having to ask.

## Clean-room reimplementation

**The implementation in this repository is a clean-room reimplementation of the
design. No branch-735 source code was copied.**

The only inputs to this implementation were:

1. **The documented pipeline design** — the sequence normalize → lexicon scan →
   fuzzy pass → match report, recorded in this repository's architecture
   decision records (see [`docs/adr/0001-single-repo-and-tech-stack.md`](docs/adr/0001-single-repo-and-tech-stack.md))
   and its design documentation.
2. **The behavioral specification preserved in this repository** — the
   observable contract the tests assert (spans, score tiers, overlap
   resolution, normalization, determinism), expressed as this repo's own test
   suite.

Design and behavior are ideas and interfaces, not source. Everything under
[`src/`](src/) was written for this repository against that design and that
specification. The branch-735 source was not consulted while writing it and no
part of it was carried over.

## Where this sits

This statement ships in the repository alongside the [MIT license](LICENSE): the
license says how the code may be used, and this note says where it came from.
Both are meant to be read together by anyone evaluating lexiqr for use or
contribution.

## Release prerequisite

Settling provenance is a **hard prerequisite of the `v1.0.0` tag**. Publishing
1.0 without this note in place, and without its wording standing as the
maintainer's own considered position, is not a valid 1.0.0.

This is enforced as a **release-checklist item, deliberately not as a CI check.**
A gate that asserts "this file exists" would give false assurance about a
question CI cannot actually answer: whether the provenance position is true and
stood behind. That judgment is a one-time human one, recorded here in writing,
and confirmed on the release checklist before the tag is pushed.
