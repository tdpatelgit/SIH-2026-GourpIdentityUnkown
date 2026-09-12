"""Real OCR via TrOCR (microsoft/trocr-base-printed), gated behind USE_REAL_OCR.

Given image bytes: preprocess (deskew/denoise/contrast via
image_preprocessing.py) -> run TrOCR -> map the raw decoded text into
human-readable fields (via ocr_field_mapper.py) shaped like the mocked
fixtures, so the reviewer sees the same kind of field table either way.

Model loads lazily on first call and is cached for the process lifetime —
loading ~1.3GB of weights on every request would make the demo unusable.
"""
import io
import os
from typing import List, Optional

from ocr_field_mapper import MappedField, build_human_readable_fields

USE_REAL_OCR = os.getenv("USE_REAL_OCR", "false").lower() in ("1", "true", "yes")

_processor = None
_model = None
_load_error: Optional[str] = None


def _lazy_load():
    global _processor, _model, _load_error
    if _processor is not None or _load_error is not None:
        return
    try:
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel

        _processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-printed")
        _model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-printed")
        _model.eval()
    except Exception as exc:  # pragma: no cover - depends on network/model download
        _load_error = str(exc)


def is_available() -> bool:
    """Whether real OCR is both enabled (USE_REAL_OCR env flag) and its
    model has loaded successfully. Used for the server-wide default and
    the /api/ocr-status diagnostic endpoint."""
    if not USE_REAL_OCR:
        return False
    _lazy_load()
    return _model is not None


def is_model_ready() -> bool:
    """Whether the TrOCR model has loaded successfully, ignoring the
    USE_REAL_OCR env flag entirely — used for the per-upload AI-review
    toggle, which lets a user request real OCR on demand regardless of
    the server's default mode."""
    _lazy_load()
    return _model is not None


def get_load_error() -> Optional[str]:
    return _load_error


def run_ocr(image_bytes: bytes) -> str:
    """Run TrOCR on preprocessed image bytes, return the recognized text.

    Raises RuntimeError if the model isn't available (caller should check
    is_available() first and fall back to mocked fixtures instead).
    """
    _lazy_load()
    if _model is None or _processor is None:
        raise RuntimeError(f"TrOCR model not available: {_load_error or 'unknown error'}")

    from PIL import Image
    import torch

    from image_preprocessing import preprocess_for_ocr

    preprocessed_bytes = preprocess_for_ocr(image_bytes)
    image = Image.open(io.BytesIO(preprocessed_bytes)).convert("RGB")
    pixel_values = _processor(images=image, return_tensors="pt").pixel_values

    with torch.no_grad():
        generated_ids = _model.generate(pixel_values, max_length=64)

    text = _processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return text.strip()


def run_ocr_and_map_fields(image_bytes: bytes) -> List[MappedField]:
    """Run OCR and return human-readable fields in the same shape as the
    mocked fixtures (list of {name, label, value, confidence})."""
    raw_text = run_ocr(image_bytes)
    return build_human_readable_fields(raw_text)


def run_ocr_multiline_and_map_fields(line_image_bytes_list: List[bytes]) -> List[MappedField]:
    """TrOCR is a single-text-line model — feeding it a multi-line scan
    garbles everything. This runs OCR on each pre-cropped single-line
    image separately, joins the decoded lines, and maps the combined
    text into human-readable fields. Used for documents split into one
    image per line/field (e.g. the demo dummy scans)."""
    lines = [run_ocr(image_bytes) for image_bytes in line_image_bytes_list]
    combined_text = "\n".join(lines)
    return build_human_readable_fields(combined_text)
