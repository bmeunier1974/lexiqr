"""Canonical serialization of a MatchReport — public, semver-governed API.

These tests exercise the serialization the way an integrating developer does:
through the public surface (`from lexiqr import serialize_report`), asserting the
observable canonical string, never the internal payload it is built from. That
is the whole point — the serialization is the contract, so the tests hold it to
its contract and nothing narrower.
"""

import json

import pytest

import lexiqr
from conftest import FLOOFF_LEXICON
from lexiqr import (
    EntityMatch,
    EntityResolver,
    MatchReport,
    Metadata,
    ScoreTier,
    deserialize_report,
    serialize_report,
)


def a_report() -> MatchReport:
    return MatchReport(
        prompt="wo ist flooff",
        locale="de-DE",
        matches=(
            EntityMatch(
                canonical_id="product",
                entry_id="product",
                surface_form="flooff",
                span=(7, 13),
                score_tier=ScoreTier.PREFERRED,
                matched_locale="de-DE",
                correction=None,
            ),
        ),
    )


def test_serialize_and_deserialize_are_part_of_the_public_api() -> None:
    assert "serialize_report" in lexiqr.__all__
    assert "deserialize_report" in lexiqr.__all__


def test_serializing_a_report_produces_a_string() -> None:
    assert isinstance(serialize_report(a_report()), str)


def test_two_equal_reports_serialize_to_byte_identical_output() -> None:
    assert serialize_report(a_report()) == serialize_report(a_report())


def test_the_canonical_string_has_sorted_keys_no_whitespace_and_a_span_array() -> None:
    serialized = serialize_report(a_report())

    assert serialized == (
        '{"locale":"de-DE","matches":['
        '{"canonical_id":"product","correction":null,"entry_id":"product",'
        '"matched_locale":"de-DE","metadata":{},"score_tier":"preferred",'
        '"span":[7,13],"surface_form":"flooff"}],'
        '"prompt":"wo ist flooff"}'
    )


def test_the_match_list_keeps_the_reports_order_rather_than_re_sorting_it() -> None:
    # Two matches whose canonical IDs are in descending order: a serializer that
    # sorted collections would flip them; a canonical one preserves the ranking
    # the pipeline chose.
    report = MatchReport(
        prompt="b a",
        locale="en-US",
        matches=(
            EntityMatch("zebra", "zebra", "b", (0, 1), ScoreTier.PREFERRED, "en-US"),
            EntityMatch("apple", "apple", "a", (2, 3), ScoreTier.PREFERRED, "en-US"),
        ),
    )

    payload = json.loads(serialize_report(report))

    assert [m["canonical_id"] for m in payload["matches"]] == ["zebra", "apple"]


def test_non_ascii_text_is_escaped_so_the_form_carries_no_encoding_choice() -> None:
    report = MatchReport(prompt="wo ist épisodes", locale="fr-FR", matches=())

    serialized = serialize_report(report)

    assert "\\u00e9" in serialized  # é, escaped rather than emitted as raw bytes
    assert serialized.isascii()


def test_a_report_round_trips_through_serialize_and_deserialize() -> None:
    report = a_report()

    assert deserialize_report(serialize_report(report)) == report


def test_deserializing_then_reserializing_yields_the_identical_string() -> None:
    serialized = serialize_report(a_report())

    assert serialize_report(deserialize_report(serialized)) == serialized


def test_a_report_with_a_correction_round_trips() -> None:
    report = MatchReport(
        prompt="wo ist floof",
        locale="de-DE",
        matches=(
            EntityMatch(
                "product",
                "product",
                "flooff",
                (7, 12),
                ScoreTier.PREFERRED,
                "de-DE",
                "floof",
            ),
        ),
    )

    assert deserialize_report(serialize_report(report)) == report


def test_two_transform_calls_with_the_same_inputs_serialize_identically() -> None:
    resolver = EntityResolver.from_file(FLOOFF_LEXICON)

    first = serialize_report(resolver.transform("wo ist flooff", "de-DE"))
    second = serialize_report(resolver.transform("wo ist flooff", "de-DE"))

    assert first == second


def a_discriminated_report() -> MatchReport:
    """A match from an entry that resolves elsewhere and carries a filter."""
    return MatchReport(
        prompt="wo sind die filme",
        locale="de-DE",
        matches=(
            EntityMatch(
                canonical_id="product",
                entry_id="movie",
                surface_form="filme",
                span=(12, 17),
                score_tier=ScoreTier.PREFERRED,
                matched_locale="de-DE",
                metadata=Metadata(
                    {"genre": ("drama", "thriller"), "productType": "Movie"}
                ),
            ),
        ),
    )


def test_the_entry_and_its_filter_are_always_emitted_never_conditionally() -> None:
    """No asymmetry between a report that used the feature and one that did not.

    A consumer's parser reads the same shape either way, so it never has to branch
    on whether a key is present — and a snapshot of one report is comparable in
    shape to a snapshot of any other.
    """
    plain = json.loads(serialize_report(a_report()))["matches"][0]
    discriminated = json.loads(serialize_report(a_discriminated_report()))["matches"][0]

    assert plain.keys() == discriminated.keys()
    assert (plain["entry_id"], plain["metadata"]) == ("product", {})
    assert discriminated["entry_id"] == "movie"


def test_a_filter_is_emitted_as_an_object_with_sorted_keys_and_stays_ascii() -> None:
    serialized = serialize_report(a_discriminated_report())

    assert (
        '"metadata":{"genre":["drama","thriller"],"productType":"Movie"}' in serialized
    )
    assert serialized.isascii()


def test_a_report_carrying_a_filter_round_trips_and_re_serializes_identically() -> None:
    report = a_discriminated_report()

    serialized = serialize_report(report)

    assert deserialize_report(serialized) == report
    assert serialize_report(deserialize_report(serialized)) == serialized


def test_a_deserialized_filter_is_still_immutable() -> None:
    """Round-tripping must not hand back a plain dict: a report read from storage
    carries the same guarantee as one just produced."""
    metadata = (
        deserialize_report(serialize_report(a_discriminated_report()))
        .matches[0]
        .metadata
    )

    assert isinstance(metadata, Metadata)
    with pytest.raises(TypeError):
        metadata["productType"] = "Series"  # type: ignore[index]
