"""Tests for ocr_engine.py — mocked, no real model download (that's
integration-tested separately / manually, since it needs ~1.3GB pulled
from HuggingFace and is too slow/network-dependent for the unit suite).
"""
import importlib

import ocr_engine as ocr_module


def _reset_module_state(monkeypatch):
    monkeypatch.setattr(ocr_module, "_processor", None)
    monkeypatch.setattr(ocr_module, "_model", None)
    monkeypatch.setattr(ocr_module, "_load_error", None)


def test_is_available_false_when_flag_disabled(monkeypatch):
    _reset_module_state(monkeypatch)
    monkeypatch.setattr(ocr_module, "USE_REAL_OCR", False)
    assert ocr_module.is_available() is False


def test_is_available_true_when_model_loads(monkeypatch):
    _reset_module_state(monkeypatch)
    monkeypatch.setattr(ocr_module, "USE_REAL_OCR", True)

    def fake_lazy_load():
        ocr_module._model = object()
        ocr_module._processor = object()

    monkeypatch.setattr(ocr_module, "_lazy_load", fake_lazy_load)
    assert ocr_module.is_available() is True


def test_is_available_false_when_model_fails_to_load(monkeypatch):
    _reset_module_state(monkeypatch)
    monkeypatch.setattr(ocr_module, "USE_REAL_OCR", True)

    def fake_lazy_load():
        ocr_module._load_error = "network unreachable"

    monkeypatch.setattr(ocr_module, "_lazy_load", fake_lazy_load)
    assert ocr_module.is_available() is False
    assert ocr_module.get_load_error() == "network unreachable"


def test_run_ocr_raises_when_model_unavailable(monkeypatch):
    _reset_module_state(monkeypatch)
    monkeypatch.setattr(ocr_module, "_lazy_load", lambda: None)
    try:
        ocr_module.run_ocr(b"fake-bytes")
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "not available" in str(exc)
