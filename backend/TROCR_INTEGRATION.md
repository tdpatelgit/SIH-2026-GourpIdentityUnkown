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

## Known environment gotcha hit during setup

`huggingface_hub` calls failed with `401 RepositoryNotFoundError` /
"OAuth token has expired" even for this fully-public model, because an
**expired cached HF token** at `~/.cache/huggingface/token` was being sent
with every request. Moved aside (`token` -> `token.expired.bak`) to let
requests fall back to anonymous access, which fixed it immediately. If
you hit the same error on another machine, check for a stale token there
too, or run `hf auth logout`.
