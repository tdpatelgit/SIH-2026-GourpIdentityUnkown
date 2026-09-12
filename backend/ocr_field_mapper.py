"""Turn raw TrOCR text into the same human-readable field shape used by the
mocked fixtures (khata_no/khasra_no/survey_no/owner_name/area/mutation),
instead of dumping one opaque "raw_ocr_text" blob on the reviewer.

This is intentionally simple, regex/keyword-based extraction — not a real
NER model. TrOCR has no concept of field boundaries, so we're pattern-
matching common label phrasing + nearby values out of a single decoded
string. Real scanned documents with inconsistent layouts will need a
proper NER model or per-field image cropping; this is a readability layer
on top of whatever TrOCR actually produced, not a claim of higher OCR
accuracy.
"""
import re
from typing import List, Optional, TypedDict


class MappedField(TypedDict):
    name: str
    label: str
    value: str
    confidence: float


# label patterns (case-insensitive) mapped to our canonical field names,
# tried in order — first match per field wins.
_FIELD_PATTERNS = [
    ("khata_no", "Khata No.", [
        r"khata\s*(?:no\.?|number)?\s*[:\-]?\s*([A-Za-z0-9/\-]+)",
    ]),
    ("khasra_no", "Khasra No.", [
        r"khasra\s*(?:no\.?|number)?\s*[:\-]?\s*([A-Za-z0-9/\-]+)",
    ]),
    ("survey_no", "Survey No.", [
        r"survey\s*(?:no\.?|number)?\s*[:\-]?\s*([A-Za-z0-9/\-]+)",
    ]),
    ("owner_name", "Owner Name", [
        r"owner(?:\s*name)?\s*[:\-]?\s*([A-Za-z][A-Za-z .]{2,40})",
    ]),
    ("area", "Area (acres)", [
        r"area\s*(?:\(acres\))?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
    ]),
    ("mutation", "Mutation", [
        r"mutation\s*(?:status)?\s*[:\-]?\s*(pending|approved|disputed)",
    ]),
]


def map_ocr_text_to_fields(raw_text: str) -> List[MappedField]:
    """Try to pull known field labels out of raw OCR text. Any field not
    matched is simply omitted — we never fabricate a value. If nothing at
    all matches, the caller falls back to showing the raw text as-is."""
    fields: List[MappedField] = []
    for name, label, patterns in _FIELD_PATTERNS:
        value = _first_match(raw_text, patterns)
        if value:
            fields.append(
                {
                    "name": name,
                    "label": label,
                    "value": value.strip(),
                    # Regex-matched from raw OCR — always lower/flagged
                    # confidence than the model's own decode confidence
                    # would be, since this layer can mis-parse boundaries.
                    "confidence": 0.55,
                }
            )
    return fields


def _first_match(text: str, patterns: List[str]) -> Optional[str]:
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def build_human_readable_fields(raw_text: str) -> List[MappedField]:
    """Public entry point: map what we can, and if literally nothing
    matched known field labels, fall back to a single readable
    'Raw OCR Text' field so the reviewer still sees *something* instead
    of an empty table."""
    mapped = map_ocr_text_to_fields(raw_text)
    if mapped:
        return mapped
    return [
        {
            "name": "raw_ocr_text",
            "label": "Raw OCR Text (unmapped)",
            "value": raw_text.strip() or "(no text recognized)",
            "confidence": 0.5,
        }
    ]
