"""Real OCR via TrOCR (microsoft/trocr-base-printed), gated behind USE_REAL_OCR.

This module is intentionally isolated from the mocked fixtures pipeline —
it does ONE thing: given image bytes, return the raw recognized text.
Field-level extraction (mapping text -> khata_no/owner_name/etc.) is
explicitly out of scope here; see README for why.

Model loads lazily on first call and is cached for the process lifetime —
loading ~1.3GB of weights on every request would make the demo unusable.
"""
import io
import os
from typing import Optional

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
    """Whether real OCR is both enabled and its model has loaded successfully."""
    if not USE_REAL_OCR:
        return False
    _lazy_load()
    return _model is not None


def get_load_error() -> Optional[str]:
    return _load_error


def run_ocr(image_bytes: bytes) -> str:
    """Run TrOCR on raw image bytes, return the recognized text.

    Raises RuntimeError if the model isn't available (caller should check
    is_available() first and fall back to mocked fixtures instead).
    """
    _lazy_load()
    if _model is None or _processor is None:
        raise RuntimeError(f"TrOCR model not available: {_load_error or 'unknown error'}")

    from PIL import Image
    import torch

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    pixel_values = _processor(images=image, return_tensors="pt").pixel_values

    with torch.no_grad():
        generated_ids = _model.generate(pixel_values, max_length=64)

    text = _processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return text.strip()
