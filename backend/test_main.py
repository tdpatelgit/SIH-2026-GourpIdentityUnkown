import io
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def _upload(filename="khata_page_03.jpg", token=None):
    file_content = io.BytesIO(b"fake-image-bytes")
    headers = {"X-Auth-Token": token} if token else {}
    return client.post(
        "/api/analyze",
        files={"file": (filename, file_content, "image/jpeg")},
        headers=headers,
    )


def test_analyze_returns_expected_shape():
    response = _upload()
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "khata_page_03.jpg"
    assert "document_id" in body
    assert "processed_at" in body
    assert len(body["fields"]) == 6
    assert isinstance(body["overall_confidence"], float)
    assert isinstance(body["review_required"], bool)
    assert body["status"] in ("pending_review", "auto_approved")
    assert body["owner_username"] is None


def test_analyze_missing_file_returns_422():
    response = client.post("/api/analyze")
    assert response.status_code == 422


def test_list_documents_includes_uploaded_doc():
    upload = _upload("khata_page_99.jpg")
    doc_id = upload.json()["document_id"]
    response = client.get("/api/documents")
    assert response.status_code == 200
    ids = [d["document_id"] for d in response.json()["documents"]]
    assert doc_id in ids


def test_approve_document_updates_status():
    upload = _upload("khata_page_88.jpg")
    doc_id = upload.json()["document_id"]
    response = client.post(f"/api/documents/{doc_id}/approve")
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_approve_missing_document_returns_404():
    response = client.post("/api/documents/doc_missing/approve")
    assert response.status_code == 404


def test_save_boundary_requires_three_points():
    upload = _upload("khata_page_77.jpg")
    doc_id = upload.json()["document_id"]
    response = client.post(f"/api/documents/{doc_id}/boundary", json={"points": [[1, 1], [2, 2]]})
    assert response.status_code == 422


def test_save_boundary_success_updates_status_and_points():
    upload = _upload("khata_page_66.jpg")
    doc_id = upload.json()["document_id"]
    points = [[1, 1], [2, 2], [3, 1]]
    response = client.post(f"/api/documents/{doc_id}/boundary", json={"points": points})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "boundary_drawn"
    assert body["boundary"] == points


def test_signup_then_login_roundtrip():
    signup = client.post("/api/auth/signup", json={"username": "farmer1", "password": "hunter2"})
    assert signup.status_code == 200
    assert "token" in signup.json()

    login = client.post("/api/auth/login", json={"username": "farmer1", "password": "hunter2"})
    assert login.status_code == 200
    assert login.json()["username"] == "farmer1"


def test_signup_rejects_duplicate_username():
    client.post("/api/auth/signup", json={"username": "farmer2", "password": "pw"})
    dup = client.post("/api/auth/signup", json={"username": "farmer2", "password": "other"})
    assert dup.status_code == 409


def test_login_rejects_wrong_password():
    client.post("/api/auth/signup", json={"username": "farmer3", "password": "correct"})
    bad_login = client.post("/api/auth/login", json={"username": "farmer3", "password": "wrong"})
    assert bad_login.status_code == 401


def test_upload_with_token_sets_owner_and_mine_filters_correctly():
    signup = client.post("/api/auth/signup", json={"username": "farmer4", "password": "pw"})
    token = signup.json()["token"]

    upload = _upload("khata_page_55.jpg", token=token)
    assert upload.status_code == 200
    assert upload.json()["owner_username"] == "farmer4"

    mine = client.get("/api/documents", params={"mine": "true"}, headers={"X-Auth-Token": token})
    ids = [d["document_id"] for d in mine.json()["documents"]]
    assert upload.json()["document_id"] in ids

    # a doc uploaded without a token should not show up under "mine" for this user
    other_upload = _upload("khata_page_44.jpg")
    other_id = other_upload.json()["document_id"]
    mine_again = client.get("/api/documents", params={"mine": "true"}, headers={"X-Auth-Token": token})
    ids_again = [d["document_id"] for d in mine_again.json()["documents"]]
    assert other_id not in ids_again


def test_reject_document_sets_status_and_reason():
    upload = _upload("khata_page_33.jpg")
    doc_id = upload.json()["document_id"]
    response = client.post(f"/api/documents/{doc_id}/reject", json={"reason": "Owner name doesn't match records"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["rejection_reason"] == "Owner name doesn't match records"


def test_reject_document_requires_non_empty_reason():
    upload = _upload("khata_page_22.jpg")
    doc_id = upload.json()["document_id"]
    response = client.post(f"/api/documents/{doc_id}/reject", json={"reason": "   "})
    assert response.status_code == 422


def test_reject_missing_document_returns_404():
    response = client.post("/api/documents/doc_missing/reject", json={"reason": "bad data"})
    assert response.status_code == 404


def test_blacklist_document_creates_entry():
    upload = _upload("khata_page_11.jpg")
    doc_id = upload.json()["document_id"]
    response = client.post(
        f"/api/documents/{doc_id}/blacklist",
        json={"reason": "AI extracted the wrong khasra number", "flagged_by": "LR-EMP-01"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == doc_id
    assert body["reason"] == "AI extracted the wrong khasra number"
    assert body["resolved"] is False


def test_blacklist_document_requires_reason():
    upload = _upload("khata_page_10.jpg")
    doc_id = upload.json()["document_id"]
    response = client.post(f"/api/documents/{doc_id}/blacklist", json={"reason": ""})
    assert response.status_code == 422


def test_blacklist_missing_document_returns_404():
    response = client.post("/api/documents/doc_missing/blacklist", json={"reason": "bad data"})
    assert response.status_code == 404


def test_list_blacklist_includes_new_entry_and_filters_by_resolved():
    upload = _upload("khata_page_09b.jpg")
    doc_id = upload.json()["document_id"]
    flag = client.post(f"/api/documents/{doc_id}/blacklist", json={"reason": "suspicious owner name"})
    entry_id = flag.json()["id"]

    unresolved = client.get("/api/blacklist", params={"resolved": "false"})
    ids = [e["id"] for e in unresolved.json()["entries"]]
    assert entry_id in ids

    resolved = client.get("/api/blacklist", params={"resolved": "true"})
    ids_resolved = [e["id"] for e in resolved.json()["entries"]]
    assert entry_id not in ids_resolved


def test_resolve_blacklist_dismissed_does_not_change_document_status():
    upload = _upload("khata_page_08b.jpg")
    doc_id = upload.json()["document_id"]
    original_status = upload.json()["status"]
    flag = client.post(f"/api/documents/{doc_id}/blacklist", json={"reason": "flagged in error"})
    entry_id = flag.json()["id"]

    response = client.post(
        f"/api/blacklist/{entry_id}/resolve",
        json={"resolution": "dismissed", "resolved_by": "admin1"},
    )
    assert response.status_code == 200
    assert response.json()["resolved"] is True
    assert response.json()["resolution"] == "dismissed"

    doc = client.get(f"/api/documents/{doc_id}").json()
    assert doc["status"] == original_status


def test_resolve_blacklist_document_rejected_also_rejects_the_document():
    upload = _upload("khata_page_07b.jpg")
    doc_id = upload.json()["document_id"]
    flag = client.post(f"/api/documents/{doc_id}/blacklist", json={"reason": "wrong survey number"})
    entry_id = flag.json()["id"]

    response = client.post(
        f"/api/blacklist/{entry_id}/resolve",
        json={"resolution": "document_rejected", "resolved_by": "admin1"},
    )
    assert response.status_code == 200

    doc = client.get(f"/api/documents/{doc_id}").json()
    assert doc["status"] == "rejected"
    assert doc["rejection_reason"] is not None


def test_resolve_blacklist_rejects_invalid_resolution_value():
    upload = _upload("khata_page_06b.jpg")
    doc_id = upload.json()["document_id"]
    flag = client.post(f"/api/documents/{doc_id}/blacklist", json={"reason": "test"})
    entry_id = flag.json()["id"]

    response = client.post(f"/api/blacklist/{entry_id}/resolve", json={"resolution": "not_a_real_value"})
    assert response.status_code == 422


def test_resolve_missing_blacklist_entry_returns_404():
    response = client.post("/api/blacklist/flag_missing/resolve", json={"resolution": "dismissed"})
    assert response.status_code == 404
