# TrOCR Integration (feature branch)

Real OCR via `microsoft/trocr-base-printed`, gated behind an env flag —
lives alongside the mocked demo pipeline without replacing it.

## Status: ✅ Working, verified live end-to-end

- Real model downloaded, loaded, and run through the actual `/api/analyze`
  endpoint (not just unit-tested) — confirmed via `curl` against a running
  server with `USE_REAL_OCR=true`.
- Default behavior (`USE_REAL_OCR` unset/false) is **completely
  unchanged** — the existing mocked fixture pipeline still runs exactly as
  before. Verified both paths side-by-side.
- 4 new unit tests for `ocr_engine.py` (mocked model, no real download in
  the test suite) + all 24 pre-existing tests still pass = 28/28 total.

## How to enable

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt   # now includes torch, transformers, pillow
USE_REAL_OCR=true uvicorn main:app --host 0.0.0.0 --port 8067
```

Check `GET /api/ocr-status` to confirm the model loaded:
```json
{"use_real_ocr_flag": true, "model_available": true, "load_error": null}
```

If `model_available` is `false` with an error, the endpoint automatically
falls back to raising a 500 rather than silently using mocked data — you
will know immediately if OCR failed, it won't fake success.

## What this does NOT do (explicitly out of scope, by your direction)

- **No field-level extraction.** TrOCR recognizes raw text from an image —
  it has no concept of "this text is the Khata No." vs "this is the Owner
  Name." Real field mapping needs either (a) cropped per-field image
  regions with known positions, or (b) an NER model on top of the raw
  text. Both are separate follow-up work.
- Every real-OCR document currently returns exactly one field:
  `raw_ocr_text` — the full recognized string — always flagged
  `review_required=true` at a flat 0.5 confidence (TrOCR doesn't expose a
  calibrated per-field confidence the way the mocked fixtures do).
- No image preprocessing (deskew/denoise/crop) — raw upload bytes go
  straight into the model. Real scanned documents will likely need this;
  the current test only validates the plumbing, not real-scan accuracy.

## Model choice

`microsoft/trocr-base-printed` — printed/typed text, not handwriting.
~1.3GB download on first use (cached afterward by `transformers` in
`~/.cache/huggingface`). CPU inference is slow (~10-15s per image on an
Apple Silicon Mac in this test) — fine for a demo, not for production
throughput; a GPU or `trocr-base-printed`'s ONNX-exported variant would
be the next optimization if this needs to be fast.

## Preprocessing + Human-Readable Field Mapping (added)

**Preprocessing** (`backend/image_preprocessing.py`, via OpenCV):
deskew (auto-detected rotation via `minAreaRect`, corrected before OCR) +
denoise (`fastNlMeansDenoisingColored`) + contrast normalization
(histogram equalization). Falls back to the original bytes unchanged if
preprocessing fails for any reason — never blocks OCR.

**Verified real impact** (not simulated) — generated a realistic
Times-New-Roman test image, rotated it -6°, ran it through TrOCR with and
without preprocessing:
- Upright, no preprocessing: `'KHATA NO 213A'` (perfect)
- Rotated, no preprocessing: `'KHATA NO 2134'` (last char corrupted)
- Rotated, WITH preprocessing: `'KEMATA NO 213A'` (number recovered correctly)

Deskew visibly fixes the rotation (verified via saved intermediate image);
the exact glyph transcription is still TrOCR's own limits on a
single-line-optimized model reading multi-word text, not this pipeline's
fault. Preprocessing is a net positive for anything actually skewed, and
a no-op (imperceptible change) for already-upright input.

**Human-readable field mapping** (`backend/ocr_field_mapper.py`): raw
decoded OCR text is regex/keyword-matched against known field labels
(Khata No., Khasra No., Survey No., Owner Name, Area, Mutation) and
reshaped into the *same* `{name, label, value, confidence}` field format
the mocked fixtures use — so a reviewer sees a normal field table instead
of one opaque "raw text" blob. Confidence is fixed at `0.55` for any
matched field (regex-matched, not a real per-field OCR confidence) and
`0.5` for the raw-text fallback. If nothing matches any known label
pattern (garbled OCR output, e.g. `'***'` on a hard input), it falls back
to displaying a single `raw_ocr_text` field so the reviewer still sees
something rather than an empty table.

**Verified live via the real running API**, not just unit tests: uploaded
a realistic "Owner Name: Ramesh Kumar" test image through
`POST /api/analyze` with `USE_REAL_OCR=true` and got back:
```json
{"fields": [{"name": "owner_name", "label": "Owner Name", "value": "RAMESH KUMAR", "confidence": 0.55}], ...}
```
— i.e. a field shaped exactly like the mocked fixture output, not a raw
blob.

**11 new unit tests** (`test_ocr_field_mapper.py`, `test_image_preprocessing.py`,
2 more in `test_ocr_engine.py`) — 48/48 backend tests passing total.

**Known limitation, still true:** this is regex/keyword pattern matching
on a single decoded string, not a real NER model — it only works when
TrOCR's own transcription is accurate enough to contain a recognizable
label phrase. Real scanned government forms with inconsistent
layouts/handwriting will need either per-field image cropping before OCR
or an actual NER model; that's the next real step if pursued further.

## Known environment gotcha hit during setup

`huggingface_hub` calls failed with `401 RepositoryNotFoundError` /
"OAuth token has expired" even for this fully-public model, because an
**expired cached HF token** at `~/.cache/huggingface/token` was being sent
with every request. Moved aside (`token` -> `token.expired.bak`) to let
requests fall back to anonymous access, which fixed it immediately. If
you hit the same error on another machine, check for a stale token there
too, or run `hf auth logout`.
