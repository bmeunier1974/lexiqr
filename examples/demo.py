"""A full sample run: one command that demonstrates lexiqr's whole contract.

    uv run python examples/demo.py

Each section states a claim, prints what lexiqr actually produced, and asserts
it. So this is a verification as well as a transcript: a section whose claim
turns out to be false raises, and the run exits non-zero naming the section that
broke. Reading the output tells you what the library does; a zero exit code
tells you it still does it.

It resolves `medien.lexicon.json` — a German media tenant with three locales,
two entries resolving to one `product` entity with distinguishing metadata, an
Austrian variant, plurals, alternates, an accented form, Arabic, a plain entry
carrying neither target nor metadata, and a multi-word label containing a
shorter one.

**Read it top to bottom, and lift what you need.** It is deliberately one flat
file — its render helper, its sections, then the driver — rather than a tidy
package, because its value is being a thing you can read in one sitting and copy
a section out of. It imports nothing but `lexiqr` and the standard library, and
finds its lexicon relative to its own location, so it runs against an installed
wheel from any working directory.

Nothing here prints or resolves at import time: the module defines constants and
functions, and every effect happens inside `main`. That is what lets the test
suite import it to exercise the render helper directly, and what keeps the
golden transcript honest — an import-time side effect would be output nobody
declared.

The full output is committed beside this file as `demo.golden.txt`, and the test
suite compares the two. After an intended change to the transcript, regenerate
it rather than hand-editing:

    uv run python examples/demo.py > examples/demo.golden.txt
"""

from __future__ import annotations

import io
import sys
import textwrap
from pathlib import Path
from typing import Protocol, cast

from lexiqr import Lexicon

#: The tenant lexicon every section resolves against, found relative to this
#: file so the working directory is irrelevant.
LEXICON = Path(__file__).resolve().parent / "medien.lexicon.json"

#: How the lexicon is named in the transcript. Spelled from the path's own parts
#: rather than printed as-is: an absolute path would make the output depend on
#: the machine it ran on, and the golden would never match twice.
LEXICON_LABEL = "/".join(LEXICON.parts[-2:])

#: The transcript's width and the column its values start in. Fixed rather than
#: read from the terminal — the golden must not depend on the window it was
#: rendered in.
WIDTH = 88
LABEL_WIDTH = 10

HEADER = (
    "lexiqr — a sample run: every claim printed, every claim asserted.",
    f"lexicon: {LEXICON_LABEL}",
)

CLOSING = "OK: every section held."


# --- Rendering ---------------------------------------------------------------


def emit(label: str, text: str) -> None:
    """One labelled line of the transcript, wrapped to a fixed width.

    Every line a section prints goes through here, so the transcript has one
    shape: a short label naming what is being shown, and the value beside it.
    """
    print(
        textwrap.fill(
            text,
            width=WIDTH,
            initial_indent=f"{label:<{LABEL_WIDTH}}",
            subsequent_indent=" " * LABEL_WIDTH,
            break_long_words=False,
            break_on_hyphens=False,
        )
    )


def heading(number: int, title: str) -> None:
    """The numbered rule that opens a section."""
    print()
    print(f"--- {number}. {title} ---")
    print()


# --- The sections ------------------------------------------------------------


def a_lexicon_loads_from_a_file() -> None:
    """A tenant lexicon loads from a file: validation is construction [C2]

    The first thing an integrating developer does, and the first thing that can
    go wrong. There is no separate validate step to forget: the object handed
    back has already been checked.
    """
    lexicon = Lexicon.from_file(LEXICON)

    entities = sorted({entry.canonical_id for entry in lexicon.entries.values()})
    locales = sorted(
        {locale for entry in lexicon.entries.values() for locale in entry.locales}
    )

    emit(
        "claim",
        "Lexicon.from_file either hands back a lexicon lexiqr can trust or raises "
        "ValidationError naming where the document is wrong. Validation is "
        "construction, so a caller holding a lexicon has nothing left to check.",
    )
    emit("lexicon", LEXICON_LABEL)
    emit("entries", ", ".join(sorted(lexicon.entries)))
    emit("entities", ", ".join(entities))
    emit("locales", ", ".join(locales))
    emit("default", lexicon.default_locale)
    emit(
        "held",
        "the loader returned rather than raised, and that verdict is the "
        f"validation. The {len(lexicon.entries)} entries it read resolve to "
        f"{len(entities)} entities, so more than one entry shares an entity, and "
        "the declared default is a locale the lexicon really authors.",
    )

    assert lexicon.entries, "a lexicon that loaded declares at least one entry"
    assert all(entry.locales for entry in lexicon.entries.values()), (
        "every entry came back carrying the locales it declares; nothing was "
        "silently dropped"
    )
    assert len(entities) < len(lexicon.entries), (
        f"{len(lexicon.entries)} entries resolve to {len(entities)} entities, so "
        f"at least two of them share one — which is what makes this lexicon "
        f"worth demonstrating"
    )
    assert lexicon.default_locale in locales, (
        f"the declared default {lexicon.default_locale!r} is one of the locales "
        f"the lexicon authors ({', '.join(locales)})"
    )


# --- The driver --------------------------------------------------------------


class Section(Protocol):
    """One section of the run: it prints its claim, its result, and asserts it.

    A protocol rather than a plain `Callable`, because the driver reads two
    things off a section besides calling it: its `__name__`, to name the section
    that failed, and the first line of its docstring, which is its title in the
    transcript.
    """

    __name__: str

    def __call__(self) -> None: ...


#: Every section, in the order the transcript prints them. Position is the
#: section number, so adding one here is the whole edit.
SECTIONS: tuple[Section, ...] = (a_lexicon_loads_from_a_file,)


def title_of(section: Section) -> str:
    """A section's title: the first line of its docstring."""
    documentation = section.__doc__
    assert documentation is not None, f"{section.__name__} has no docstring to title it"
    return documentation.strip().splitlines()[0].strip()


def main() -> int:
    """Print every section, assert every claim, and report whether they held."""
    # Arabic surface forms are part of what this run demonstrates, and a Windows
    # console defaults to a code page that cannot encode them. The cast is here
    # because `reconfigure` is a `TextIOWrapper` method the standard streams'
    # type stub does not advertise.
    cast(io.TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")

    for line in HEADER:
        print(line)

    for number, section in enumerate(SECTIONS, start=1):
        heading(number, title_of(section))
        try:
            section()
        except AssertionError as failed:
            print()
            print(f"FAIL in section {number} ({section.__name__}): {failed}")
            return 1

    print()
    print(CLOSING)
    return 0


if __name__ == "__main__":
    sys.exit(main())
