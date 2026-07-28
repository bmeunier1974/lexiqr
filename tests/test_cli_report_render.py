"""The pure match-report renderer: a typed `MatchReport` in, string out.

Driven by constructing core's typed values directly — no argv, process, or
captured streams. The renderer is *total* over the report type: every field a
match can carry is rendered when present and simply omitted when absent, so a
field a later epic populates (correction, a diverging matched locale) surfaces
here with no code change.

Span marking is the load-bearing behaviour: the marker is built from the
report's character offsets into the *original* prompt, never by re-searching for
the surface form — which accents and casefolding would make wrong.
"""

from lexiqr import EntityMatch, MatchReport, Metadata, ScoreTier
from lexiqr.cli._report import render_match_report
from lexiqr.metadata import EMPTY


def match(
    *,
    canonical_id: str = "product",
    entry_id: str | None = None,
    surface_form: str = "flooff",
    span: tuple[int, int] = (7, 13),
    score_tier: ScoreTier = ScoreTier.PREFERRED,
    matched_locale: str = "de-DE",
    correction: str | None = None,
    metadata: Metadata = EMPTY,
) -> EntityMatch:
    return EntityMatch(
        canonical_id=canonical_id,
        entry_id=canonical_id if entry_id is None else entry_id,
        surface_form=surface_form,
        span=span,
        score_tier=score_tier,
        matched_locale=matched_locale,
        correction=correction,
        metadata=metadata,
    )


def test_a_single_exact_match_renders_its_whole_shape() -> None:
    report = MatchReport(prompt="wo ist flooff", locale="de-DE", matches=(match(),))

    rendered = render_match_report(report)

    assert "product" in rendered  # canonical ID it resolved to
    assert "flooff" in rendered  # surface form that matched
    assert "preferred" in rendered  # score tier
    assert "de-DE" in rendered  # matched locale


def test_an_exact_match_shows_no_correction() -> None:
    report = MatchReport(prompt="wo ist flooff", locale="de-DE", matches=(match(),))

    rendered = render_match_report(report)

    assert "correction" not in rendered.lower()


def test_the_report_states_the_locale_the_prompt_resolved_through() -> None:
    report = MatchReport(
        prompt="wo ist flooff",
        locale="de-AT",
        matches=(match(matched_locale="de-AT"),),
    )

    rendered = render_match_report(report)

    assert "de-AT" in rendered


def test_the_span_is_marked_against_the_original_prompt_by_offset() -> None:
    prompt = "wo ist flooff"
    report = MatchReport(prompt=prompt, locale="de-DE", matches=(match(span=(7, 13)),))

    rendered = render_match_report(report)

    # The marked characters are exactly the original prompt's [7:13].
    assert f"[{prompt[7:13]}]" in rendered
    assert "[flooff]" in rendered


def test_the_span_marks_the_original_characters_across_a_stripped_accent() -> None:
    # The surface form is ASCII-folded and does NOT occur in the prompt: a
    # renderer that searched for it would mark nothing. Offset-based marking
    # brackets the original accented characters regardless.
    prompt = "wo ist Prämie"  # 'Prämie' is prompt[7:13]
    report = MatchReport(
        prompt=prompt,
        locale="de-DE",
        matches=(match(canonical_id="invoice", surface_form="pramie", span=(7, 13)),),
    )

    rendered = render_match_report(report)

    assert "[Prämie]" in rendered
    assert prompt[7:13] == "Prämie"


def test_the_span_marks_the_original_characters_in_a_non_latin_prompt() -> None:
    prompt = "みせて フルーフ"  # 'フルーフ' is prompt[4:8]
    report = MatchReport(
        prompt=prompt,
        locale="ja-JP",
        matches=(match(surface_form="フルーフ", span=(4, 8), matched_locale="ja-JP"),),
    )

    rendered = render_match_report(report)

    assert f"[{prompt[4:8]}]" in rendered
    assert "[フルーフ]" in rendered


def test_matches_render_in_the_order_the_report_gives_them() -> None:
    first = match(canonical_id="alpha", surface_form="aaa", span=(0, 3))
    second = match(canonical_id="bravo", surface_form="bbb", span=(4, 7))
    report = MatchReport(prompt="aaa bbb", locale="de-DE", matches=(first, second))

    rendered = render_match_report(report)

    assert rendered.index("alpha") < rendered.index("bravo")


def test_a_fuzzy_match_shows_the_correction_that_was_applied() -> None:
    report = MatchReport(
        prompt="wo ist floof",
        locale="de-DE",
        matches=(match(surface_form="flooff", span=(7, 12), correction="floof"),),
    )

    rendered = render_match_report(report)

    assert "correction" in rendered.lower()
    assert "floof" in rendered


def test_a_match_shows_a_locale_that_differs_from_the_requested_one() -> None:
    # A fallback hit: the report resolved through de-DE, but this match names the
    # locale that actually answered so a direct hit is distinguishable.
    report = MatchReport(
        prompt="wo ist flooff",
        locale="de-DE",
        matches=(match(matched_locale="de-CH"),),
    )

    rendered = render_match_report(report)

    assert "de-CH" in rendered


def test_a_zero_match_prompt_is_rendered_explicitly_not_as_silence() -> None:
    report = MatchReport(prompt="nothing here", locale="de-DE", matches=())

    rendered = render_match_report(report)

    assert "no match" in rendered.lower()
    assert "nothing here" in rendered  # the prompt is still shown
    assert "de-DE" in rendered  # and the locale it resolved through


def test_many_matches_stay_legible_one_block_per_match() -> None:
    matches = tuple(
        match(canonical_id=f"entity{i}", surface_form=f"s{i}", span=(i, i + 1))
        for i in range(6)
    )
    report = MatchReport(prompt="a" * 40, locale="de-DE", matches=matches)

    rendered = render_match_report(report)

    for i in range(6):
        assert f"entity{i}" in rendered
    # The prompt line is rendered once, not repeated per match.
    assert rendered.count("resolved via") == 1


# --- The entry that answered, and the filter it carried. Both lines are
# --- conditional, in the style `correction` already established: a lexicon that
# --- does not use the feature renders exactly as it did before it existed.


def test_a_match_from_a_discriminating_entry_names_the_entry_that_answered() -> None:
    """An author with two entries on one entity needs to see which one replied;
    the canonical ID alone cannot tell them."""
    report = MatchReport(
        prompt="wo sind die filme",
        locale="de-DE",
        matches=(
            match(canonical_id="product", entry_id="movie", surface_form="filme"),
        ),
    )

    rendered = render_match_report(report)

    assert "entry: movie" in rendered


def test_a_match_whose_entry_is_its_entity_names_no_entry() -> None:
    """Repeating the identifier would add a line saying nothing to every match of
    every lexicon that never uses the feature."""
    rendered = render_match_report(
        MatchReport(prompt="wo ist flooff", locale="de-DE", matches=(match(),))
    )

    assert "entry:" not in rendered


def test_a_match_carrying_a_filter_renders_it_with_keys_in_sorted_order() -> None:
    """Sorted, so two runs of the same command produce the same text — the same
    reason the serialization sorts."""
    report = MatchReport(
        prompt="wo sind die filme",
        locale="de-DE",
        matches=(
            match(
                canonical_id="product",
                entry_id="movie",
                surface_form="filme",
                metadata=Metadata(
                    {"productType": "Movie", "genre": ("drama", "thriller"), "age": 12}
                ),
            ),
        ),
    )

    rendered = render_match_report(report)

    assert "filter: age=12, genre=drama|thriller, productType=Movie" in rendered


def test_a_match_with_no_filter_renders_no_filter_line() -> None:
    rendered = render_match_report(
        MatchReport(prompt="wo ist flooff", locale="de-DE", matches=(match(),))
    )

    assert "filter:" not in rendered


def test_a_boolean_filter_renders_the_way_the_author_wrote_it() -> None:
    """The author typed `true` in JSON, so the report says `true`.

    Python spells it `True`; echoing that back would show a lexicon author a value
    that is not in their file, in a tool whose whole job is telling them what their
    file does.
    """
    report = MatchReport(
        prompt="wo sind die filme",
        locale="de-DE",
        matches=(
            match(
                canonical_id="product",
                entry_id="series",
                metadata=Metadata({"episodic": True, "archived": False}),
            ),
        ),
    )

    rendered = render_match_report(report)

    assert "filter: archived=false, episodic=true" in rendered
