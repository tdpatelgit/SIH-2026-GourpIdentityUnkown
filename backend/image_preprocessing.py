"""Lightweight image preprocessing before OCR: deskew, denoise, contrast
normalization. Improves TrOCR accuracy on real scanned documents, which
are rarely perfectly upright/clean like a synthetic test image.

Pure functions, no model dependency — safe to unit test without a model
download.
"""
import io

import cv2
import numpy as np
from PIL import Image


def _pil_to_cv(image: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)


def _cv_to_pil(mat: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(mat, cv2.COLOR_BGR2RGB))


def _estimate_skew_angle(gray: np.ndarray) -> float:
    """Estimate document skew via minAreaRect over thresholded foreground
    pixels. Returns degrees; small/no rotation if the image looks already
    upright or the estimate is unreliable (near-empty threshold)."""
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    if coords.shape[0] < 20:
        return 0.0
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    # Ignore wild estimates — sign of a nearly-blank or already-upright image.
    if abs(angle) > 15:
        return 0.0
    return angle


def _deskew(mat: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(mat, cv2.COLOR_BGR2GRAY)
    angle = _estimate_skew_angle(gray)
    if abs(angle) < 0.5:
        return mat
    (h, w) = mat.shape[:2]
    center = (w // 2, h // 2)
    rot_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        mat, rot_matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )


def _denoise_and_normalize_contrast(mat: np.ndarray) -> np.ndarray:
    denoised = cv2.fastNlMeansDenoisingColored(mat, None, 7, 7, 7, 21)
    gray = cv2.cvtColor(denoised, cv2.COLOR_BGR2GRAY)
    equalized = cv2.equalizeHist(gray)
    return cv2.cvtColor(equalized, cv2.COLOR_GRAY2BGR)


def preprocess_for_ocr(image_bytes: bytes) -> bytes:
    """Deskew + denoise + contrast-normalize raw image bytes, return PNG
    bytes ready for the OCR model. Falls back to the original bytes
    unchanged if preprocessing fails for any reason (never blocks OCR)."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        mat = _pil_to_cv(image)
        mat = _deskew(mat)
        mat = _denoise_and_normalize_contrast(mat)
        result = _cv_to_pil(mat)
        out = io.BytesIO()
        result.save(out, format="PNG")
        return out.getvalue()
    except Exception:
        return image_bytes
