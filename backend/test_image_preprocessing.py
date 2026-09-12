"""Unit tests for image_preprocessing.py — pure OpenCV logic, no model needed."""
import io

from PIL import Image, ImageDraw

from image_preprocessing import preprocess_for_ocr


def _make_test_image() -> bytes:
    img = Image.new("RGB", (200, 80), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 30), "KHATA NO 213A", fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_preprocess_returns_valid_image_bytes():
    original = _make_test_image()
    processed = preprocess_for_ocr(original)
    # Should decode as a valid image without raising.
    img = Image.open(io.BytesIO(processed))
    img.load()
    assert img.size[0] > 0 and img.size[1] > 0


def test_preprocess_falls_back_on_garbage_input():
    garbage = b"this is not an image"
    result = preprocess_for_ocr(garbage)
    # Falls back to returning the original bytes unchanged rather than raising.
    assert result == garbage
