"""Unit tests for ocr_field_mapper.py — pure regex logic, no model needed."""
from ocr_field_mapper import build_human_readable_fields, map_ocr_text_to_fields


def test_maps_known_fields_from_labeled_text():
    text = "Khata No: 213A Owner Name: Ramesh Kumar Area: 4.50 Mutation: Approved"
    fields = map_ocr_text_to_fields(text)
    names = {f["name"] for f in fields}
    assert "khata_no" in names
    assert "owner_name" in names
    assert "area" in names
    assert "mutation" in names

    by_name = {f["name"]: f for f in fields}
    assert by_name["khata_no"]["value"] == "213A"
    assert by_name["area"]["value"] == "4.50"
    assert by_name["mutation"]["value"].lower() == "approved"


def test_field_shape_matches_mocked_fixtures():
    text = "Khasra No: 901/B"
    fields = map_ocr_text_to_fields(text)
    assert len(fields) == 1
    field = fields[0]
    assert set(field.keys()) == {"name", "label", "value", "confidence"}
    assert isinstance(field["confidence"], float)


def test_no_matches_falls_back_to_raw_text():
    text = "some illegible garbage the ocr produced"
    fields = build_human_readable_fields(text)
    assert len(fields) == 1
    assert fields[0]["name"] == "raw_ocr_text"
    assert fields[0]["value"] == text


def test_empty_text_falls_back_with_placeholder():
    fields = build_human_readable_fields("")
    assert fields[0]["value"] == "(no text recognized)"


def test_partial_match_only_returns_matched_fields():
    text = "Owner Name: Priya Singh"
    fields = build_human_readable_fields(text)
    assert len(fields) == 1
    assert fields[0]["name"] == "owner_name"
    assert fields[0]["value"] == "Priya Singh"
