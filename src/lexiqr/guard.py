"""The input guard — the one place that decides what the pipeline will accept.

`transform()` calls this once, before normalization, so the stages behind it
(normalize, scan, fuzzy) never have to defend themselves against hostile input.
The interface is deliberately small — text in, either an accepted form or a
structured `ValidationError` out — with the whole "what input is acceptable"
policy encapsulated here. That is what makes hostile input cost a rejection
rather than a full pipeline pass, and what lets the policy be read, tested, and
changed in exactly one place.

The accepted form this guard hands on is the text *unchanged*: the guard bounds
and rejects, it never mangles. Spans reported downstream therefore keep indexing
the prompt the user actually typed.

Two of the guard's decisions are deliberately asymmetric, and both live here so
the asymmetry reads in one place. Exceeding the size limit is a *failure* — it
raises `ValidationError`. Empty or whitespace-only input is a *result* — "the
user typed nothing" is an ordinary outcome, so it resolves to an empty match
report rather than raising, and the guard says so via `is_blank` for the
pipeline to short-circuit on.

Adversarial Unicode is *bounded and rejected, never sanitized*. The size limit
already bounds the work a combining-character flood, bidi-control run, or
astral-plane blob can cost, and because the guard hands the text on unchanged,
bidi controls and astral characters resolve predictably rather than distorting
what matches. The one class the guard actively rejects is a lone surrogate: a
malformed code point that cannot be encoded to UTF-8, and so must fail at the
boundary rather than propagate into a report that could never be serialized.
"""

from __future__ import annotations

import re

from lexiqr.errors import ValidationError

#: A lone surrogate — any code point in U+D800..U+DFFF standing on its own. A
#: well-formed Python `str` never holds a *paired* surrogate (astral characters
#: are single code points), so a surrogate found here is always malformed: it
#: cannot be encoded to UTF-8, which means it could never be serialized, stored,
#: or round-tripped. The guard rejects it at the boundary rather than letting
#: bad bytes reach a report that downstream code then cannot handle.
_LONE_SURROGATE = re.compile("[\ud800-\udfff]")

#: The maximum prompt length lexiqr accepts, in Unicode code points. This is a
#: documented part of the contract, not a per-call argument or a configuration
#: knob: one number every integrating developer can reason about, stated in the
#: README. Changing it is a semver-visible change. It is set well below the size
#: at which a pasted document would threaten a request thread, so a prompt that
#: exceeds it is rejected cheaply rather than scanned.
MAX_PROMPT_LENGTH = 10_000


def check_prompt(prompt: str) -> str:
    """Return `prompt` unchanged if acceptable; raise `ValidationError` if not.

    Length is counted in code points, so the verdict does not depend on the
    platform's or interpreter's internal string representation.
    """
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise ValidationError(
            f"Prompt exceeds the maximum length of {MAX_PROMPT_LENGTH} "
            f"characters (got {len(prompt)}).",
            field="prompt",
        )
    surrogate = _LONE_SURROGATE.search(prompt)
    if surrogate is not None:
        raise ValidationError(
            f"Prompt contains a lone surrogate (U+{ord(surrogate.group()):04X}) at "
            f"position {surrogate.start()}; such malformed code points cannot be "
            f"encoded and are rejected at the input boundary.",
            field="prompt",
        )
    return prompt


def is_blank(prompt: str) -> bool:
    """Whether a prompt is empty or only whitespace — a defined empty result.

    Empty and whitespace-only input are treated identically, so a caller never
    has to pre-trim: "the user typed nothing" resolves to an empty match report,
    not a failure. Whitespace is judged by `str.strip()`, which covers spaces,
    tabs, newlines, and Unicode whitespace alike.
    """
    return not prompt.strip()
