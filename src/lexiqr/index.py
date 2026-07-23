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
from lexiqr.normalizer import normalize_text
from lexiqr.types import ScoreTier

#: A surface form only counts when it stands as a word. Without this, "ticket"
#: matches inside "tickets" and a tenant's short label matches inside half the
#: prompt.
_WORD = re.compile(r"\w")


@dataclass(frozen=True)
class Hit:
    """One occurrence of one surface form, in the coordinates it was found in.

    The span indexes the *normalized* text the scan was handed. Translating it
    back to the prompt the caller typed is the matcher's job, done once, at the
    boundary where the report is built.
    """

    canonical_id: str
    surface_form: str
    span: tuple[int, int]
    score_tier: ScoreTier


@dataclass
class _Node:
    children: dict[str, _Node] = field(default_factory=dict)
    #: Forms ending at this node, as (folded length, canonical ID, surface
    #: form, tier). Several, because two entities may declare the same surface
    #: form, and one entity may declare it in two tiers.
    outputs: list[tuple[int, str, str, ScoreTier]] = field(default_factory=list)
    fail: _Node | None = None


class SurfaceFormIndex:
    """The surface forms of one lexicon in one locale, ready to scan with."""

    def __init__(self, root: _Node) -> None:
        self._root = root

    @classmethod
    def build(cls, lexicon: Lexicon, locale: str) -> SurfaceFormIndex:
        """Compile every surface form `locale` declares.

        Forms of other locales are not compiled in, so they cannot be matched
        by accident: a caller who states a locale gets that locale's answers.
        """
        root = _Node()
        for canonical_id, locales in lexicon.entities.items():
            forms = locales.get(locale)
            if forms is None:
                continue
            seen: set[str] = set()
            for surface_form, tier in _tiered_surface_forms(canonical_id, forms):
                folded = normalize_text(surface_form, locale)
                # An entity whose canonical ID reads the same as one of its
                # labels ("invoice") declared one form, not two candidates at
                # different tiers. Best tier first means the first wins.
                if folded and folded not in seen:
                    seen.add(folded)
                    _insert(root, folded, canonical_id, surface_form, tier)
        _link_failures(root)
        return cls(root)

    def scan(self, text: str) -> tuple[Hit, ...]:
        """Every whole-word occurrence of every compiled form, in one pass."""
        hits: list[Hit] = []
        node = self._root
        for position, character in enumerate(text):
            node = _advance(node, character, self._root)
            for length, canonical_id, surface_form, tier in _outputs(node):
                start = position - length + 1
                if _stands_alone(text, start, position + 1):
                    hits.append(
                        Hit(
                            canonical_id=canonical_id,
                            surface_form=surface_form,
                            span=(start, position + 1),
                            score_tier=tier,
                        )
                    )
        return tuple(hits)


def _tiered_surface_forms(
    canonical_id: str, forms: SurfaceForms
) -> list[tuple[str, ScoreTier]]:
    """Every way a tenant's users might name this entity, best form first.

    The canonical ID is included as a surface form of last resort: a prompt
    that names the entity outright should still resolve, but a tenant's own
    vocabulary outranks the identifier they never see.
    """
    tiered = [(forms.preferred_singular, ScoreTier.PREFERRED)]
    if forms.preferred_plural is not None:
        tiered.append((forms.preferred_plural, ScoreTier.PREFERRED))
    tiered.extend((alternate, ScoreTier.ALTERNATE) for alternate in forms.alternates)
    tiered.append((canonical_id, ScoreTier.CANONICAL))
    return tiered


def _insert(
    root: _Node, folded: str, canonical_id: str, surface_form: str, tier: ScoreTier
) -> None:
    node = root
    for character in folded:
        node = node.children.setdefault(character, _Node())
    node.outputs.append((len(folded), canonical_id, surface_form, tier))


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


def _outputs(node: _Node) -> list[tuple[int, str, str, ScoreTier]]:
    """Forms ending here, plus those ending at every suffix of here.

    A node's own outputs are not the whole story: "ticket" ends inside
    "support ticket", and both are occurrences the resolver must see.
    """
    found: list[tuple[int, str, str, ScoreTier]] = []
    current: _Node | None = node
    while current is not None:
        found.extend(current.outputs)
        current = current.fail if current.fail is not current else None
    return found


def _stands_alone(text: str, start: int, end: int) -> bool:
    before = text[start - 1] if start > 0 else ""
    after = text[end] if end < len(text) else ""
    return not _WORD.match(before) and not _WORD.match(after)
