"""Tests for the per-upload AI-review toggle on /api/analyze.

Mocks ocr_engine so these run without downloading/loading the real
~1.3GB TrOCR model.
"""
import io

from fastapi.testclient import TestClient

import ocr_engine
from main import app

client = TestClient(app)


def _upload(filename="khata_page_toggle.jpg", use_ai=False):
    file_content = io.BytesIO(b"fake-image-bytes")
    return client.post(
        "/api/analyze",
        files={"file": (filename, file_content, "image/jpeg")},
        data={"use_ai": "true" if use_ai else "false"},
    )


def test_use_ai_false_uses_saved_response_fixtures(monkeypatch):
    monkeypatch.setattr(ocr_engine, "is_model_ready", lambda: True)
    response = _upload(use_ai=False)
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "saved_response"
    assert len(body["fields"]) == 6  # mocked fixture shape


def test_use_ai_true_uses_real_ocr_path(monkeypatch):
    monkeypatch.setattr(ocr_engine, "is_model_ready", lambda: True)
    monkeypatch.setattr(
        ocr_engine,
        "run_ocr_and_map_fields",
        lambda image_bytes: [
            {"name": "owner_name", "label": "Owner Name", "value": "Test AI Person", "confidence": 0.55}
        ],
    )
    response = _upload(use_ai=True)
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "ai_review"
    assert body["fields"] == [
        {"name": "owner_name", "label": "Owner Name", "value": "Test AI Person", "confidence": 0.55}
    ]
    assert body["status"] == "pending_review"


def test_use_ai_true_fails_loudly_when_model_unavailable(monkeypatch):
    monkeypatch.setattr(ocr_engine, "is_model_ready", lambda: False)
    monkeypatch.setattr(ocr_engine, "get_load_error", lambda: "model download failed")
    response = _upload(use_ai=True)
    assert response.status_code == 503
    assert "model download failed" in response.json()["detail"]


def test_use_ai_defaults_to_false():
    file_content = io.BytesIO(b"fake-image-bytes")
    response = client.post(
        "/api/analyze",
        files={"file": ("khata_page_default.jpg", file_content, "image/jpeg")},
    )
    assert response.status_code == 200
    assert response.json()["source"] == "saved_response"


def test_dummy_upload_use_ai_false_uses_fixture():
    response = client.post("/api/documents/dummy-upload", json={"plot_id": 1, "use_ai": False})
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "saved_response"
    assert len(body["fields"]) == 6


def test_dummy_upload_use_ai_true_runs_real_ocr_on_scan_image(monkeypatch):
    monkeypatch.setattr(ocr_engine, "is_model_ready", lambda: True)
    monkeypatch.setattr(
        ocr_engine,
        "run_ocr_multiline_and_map_fields",
        lambda line_bytes_list: [
            {"name": "khata_no", "label": "Khata No.", "value": "213/A", "confidence": 0.55}
        ],
    )
    response = client.post("/api/documents/dummy-upload", json={"plot_id": 1, "use_ai": True})
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "ai_review"
    assert body["fields"] == [
        {"name": "khata_no", "label": "Khata No.", "value": "213/A", "confidence": 0.55}
    ]


def test_dummy_upload_use_ai_true_fails_loudly_when_model_unavailable(monkeypatch):
    monkeypatch.setattr(ocr_engine, "is_model_ready", lambda: False)
    monkeypatch.setattr(ocr_engine, "get_load_error", lambda: "model not loaded")
    response = client.post("/api/documents/dummy-upload", json={"plot_id": 1, "use_ai": True})
    assert response.status_code == 503
