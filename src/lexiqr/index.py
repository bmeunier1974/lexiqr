"""Every surface form of one locale, in one structure that scans text once.

Matching a lexicon by looping over its surface forms and searching for each in
turn costs one pass per form. A tenant with a few hundred entities across
singulars, plurals and alternates pays that a few thousand times per prompt,
and the cost grows with the lexicon rather than with the prompt.

So the forms are compiled into an Aho-Corasick automaton: a trie of every form,
plus a failure link from each node to the longest proper suffix that is still a
prefix of some form. One pass over the text then reports every occurrence of
every form, overlaps and nesting included — which is exactly what the resolver
downstream needs to choose between, and exactly what a per-form search makes
expensive to get.

Pure Python, no dependency. The alphabet is whatever the normalizer emitted.
"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field

from lexiqr.lexicon import Lexicon, SurfaceForms
from lexiqr.metadata import EMPTY, Metadata
from lexiqr.normalizer import normalize_text
from lexiqr.types import ScoreTier

#: What counts as a word character — the one rule both passes obey, stated here
#: because the exact scan is what makes it observable. A surface form only counts
#: when it stands as a word: without this, "ticket" matches inside "tickets" and
#: a tenant's short label matches inside half the prompt. The matcher's fuzzy
#: pass cuts its residue into runs of the same class, so the words tolerance
#: examines are exactly the words the scan required to stand alone.
WORD_CHARACTER = re.compile(r"\w")


@dataclass(frozen=True)
class Hit:
    """One occurrence of one surface form, in the coordinates it was found in.

    The span indexes the *normalized* text the scan was handed. Translating it
    back to the prompt the caller typed is the matcher's job, done once, at the
    boundary where the report is built.
    """

    canonical_id: str
    #: The entry this form was declared under. Equal to the canonical ID for an
    #: entry that resolves to itself; what separates two candidates of one entity
    #: when nothing else does (see `lexiqr.ordering`).
    entry_id: str
    surface_form: str
    span: tuple[int, int]
    score_tier: ScoreTier
    #: The entry's filter, carried by reference: `Metadata` is immutable, so every
    #: hit on a form points at the one object the loader built rather than paying
    #: for a copy per hit — which is what keeps the performance envelope intact on
    #: a lexicon whose every entry declares one.
    metadata: Metadata = EMPTY

    @classmethod
    def of(cls, form: SurfaceForm, span: tuple[int, int]) -> Hit:
        """This compiled form, found at `span`.

        Both passes report through here — the exact scan when the automaton
        reaches a form's last character, the fuzzy pass when a token is close
        enough to one — so what a hit carries from the form it came from is
        decided once, and neither pass can carry less than the other.
        """
        return cls(
            canonical_id=form.canonical_id,
            entry_id=form.entry_id,
            surface_form=form.surface_form,
            span=span,
            score_tier=form.score_tier,
            metadata=form.metadata,
        )


@dataclass(frozen=True)
class SurfaceForm:
    """One declared surface form, folded once, ready to compare against.

    The exact scan reaches these through the automaton; the fuzzy pass reaches
    them through `SurfaceFormIndex.forms()`, because tolerance has to compare a
    typed token against every candidate it might be a misspelling of, not only
    the ones a prefix already led it to.
    """

    #: The form as the normalizer folded it — the alphabet the scan works in.
    folded: str
    canonical_id: str
    #: The entry this form was declared under; see `Hit.entry_id`.
    entry_id: str
    #: The form as the tenant declared it, carried untouched so a match can name
    #: what it resolved to in the tenant's own spelling.
    surface_form: str
    score_tier: ScoreTier
    #: The entry's filter; see `Hit.metadata`.
    metadata: Metadata = EMPTY


@dataclass
class _Node:
    children: dict[str, _Node] = field(default_factory=dict)
    #: The compiled forms ending at this node — the forms themselves, not a
    #: flattened copy of their fields, so what a hit carries is decided once, on
    #: `SurfaceForm`. Several, because two entries may declare the same surface
    #: form, and one entry may declare it in two tiers.
    outputs: list[SurfaceForm] = field(default_factory=list)
    fail: _Node | None = None


class SurfaceFormIndex:
    """The surface forms of one lexicon in one locale, ready to scan with."""

    def __init__(self, root: _Node, forms: tuple[SurfaceForm, ...]) -> None:
        self._root = root
        self._forms = forms

    @classmethod
    def build(cls, lexicon: Lexicon, locale: str) -> SurfaceFormIndex:
        """Compile every surface form `locale` declares.

        Forms of other locales are not compiled in, so they cannot be matched
        by accident: a caller who states a locale gets that locale's answers.
        """
        root = _Node()
        forms: list[SurfaceForm] = []
        for entry in lexicon.entries.values():
            entity_forms = entry.locales.get(locale)
            if entity_forms is None:
                continue
            canonical_id = entry.canonical_id
            seen: set[str] = set()
            for surface_form, tier in _tiered_surface_forms(
                entry.entry_id, entity_forms
            ):
                folded = normalize_text(surface_form, locale)
                # An entry whose ID reads the same as one of its own labels
                # ("invoice") declared one form, not two candidates at different
                # tiers. Best tier first means the first wins.
                #
                # The same rule settles a genuine tie determinism depends on: one
                # entry declaring two forms that fold to the same text ("café"
                # and "cafe" both fold to "cafe"). They would claim the identical
                # span at the identical tier, and nothing about the text or the
                # entry separates them — not even `ordering.identity`, which is
                # per-entry and so cannot tell one entry's two forms apart. So
                # the ordering closes here, on declaration order, keeping the
                # first-declared and never emitting a second candidate that a
                # later stage would have to break by whichever it happened to see
                # first. Declaration order is stable across runs, machines, and
                # hash seeds; this is a deliberate, deterministic behavior
                # decision, not incidental.
                if folded and folded not in seen:
                    seen.add(folded)
                    compiled = SurfaceForm(
                        folded=folded,
                        canonical_id=canonical_id,
                        entry_id=entry.entry_id,
                        surface_form=surface_form,
                        score_tier=tier,
                        metadata=entry.metadata,
                    )
                    _insert(root, compiled)
                    forms.append(compiled)
        _link_failures(root)
        return cls(root, tuple(forms))

    def forms(self) -> tuple[SurfaceForm, ...]:
        """Every compiled candidate form, for the fuzzy pass to compare against.

        The order is the tiered declaration order `build` inserted them in; the
        fuzzy pass imposes its own total ranking and does not lean on this.
        """
        return self._forms

    def scan(self, text: str) -> tuple[Hit, ...]:
        """Every whole-word occurrence of every compiled form, in one pass."""
        hits: list[Hit] = []
        node = self._root
        for position, character in enumerate(text):
            node = _advance(node, character, self._root)
            for form in _outputs(node):
                start = position - len(form.folded) + 1
                if _stands_alone(text, start, position + 1):
                    hits.append(Hit.of(form, (start, position + 1)))
        return tuple(hits)


def _tiered_surface_forms(
    entry_id: str, forms: SurfaceForms
) -> list[tuple[str, ScoreTier]]:
    """Every way a tenant's users might name this entry, best form first.

    The **entry ID** is included as a surface form of last resort: a prompt that
    names the entry outright should still resolve, but a tenant's own vocabulary
    outranks the identifier they never see.

    The entry ID, and never the canonical ID it resolves to. Otherwise every
    entry sharing a target would claim that target as a canonical-tier form, and
    they would collide over a word no tenant wrote — the word "product" is
    matchable exactly when an entry is *named* `product`. For an entry that
    resolves to itself the two are the same string, so nothing changes.
    """
    tiered = [(forms.preferred_singular, ScoreTier.PREFERRED)]
    if forms.preferred_plural is not None:
        tiered.append((forms.preferred_plural, ScoreTier.PREFERRED))
    tiered.extend((alternate, ScoreTier.ALTERNATE) for alternate in forms.alternates)
    tiered.append((entry_id, ScoreTier.CANONICAL))
    return tiered


def _insert(root: _Node, form: SurfaceForm) -> None:
    node = root
    for character in form.folded:
        node = node.children.setdefault(character, _Node())
    node.outputs.append(form)


def _link_failures(root: _Node) -> None:
    """Breadth-first, so a node's failure target is linked before the node is."""
    root.fail = root
    queue: deque[_Node] = deque()
    for child in root.children.values():
        child.fail = root
        queue.append(child)
    while queue:
        node = queue.popleft()
        for character, child in node.children.items():
            child.fail = _advance(node.fail or root, character, root)
            queue.append(child)


def _advance(node: _Node, character: str, root: _Node) -> _Node:
    """Follow `character`, falling back along failure links until something fits."""
    while character not in node.children and node is not root:
        node = node.fail or root
    return node.children.get(character, root)


def _outputs(node: _Node) -> list[SurfaceForm]:
    """Forms ending here, plus those ending at every suffix of here.

    A node's own outputs are not the whole story: "ticket" ends inside
    "support ticket", and both are occurrences the resolver must see.
    """
    found: list[SurfaceForm] = []
    current: _Node | None = node
    while current is not None:
        found.extend(current.outputs)
        current = current.fail if current.fail is not current else None
    return found


def _stands_alone(text: str, start: int, end: int) -> bool:
    before = text[start - 1] if start > 0 else ""
    after = text[end] if end < len(text) else ""
    return not WORD_CHARACTER.match(before) and not WORD_CHARACTER.match(after)
