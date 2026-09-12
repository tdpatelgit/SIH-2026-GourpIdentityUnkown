import asyncio
import random
import uuid
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import db
import government_records
import ocr_engine
from dummy_plot_fixtures import get_dummy_fixture
from fixtures import pick_fixture

app = FastAPI(title="Land Record Digitizer — Mock API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    db.init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- auth (uploader accounts — separate from the mocked Gov Employee login) ----------

class AuthPayload(BaseModel):
    username: str
    password: str


@app.post("/api/auth/signup")
def signup(payload: AuthPayload):
    result = db.create_user(payload.username.strip(), payload.password)
    if not result:
        raise HTTPException(status_code=409, detail="username already taken")
    return result


@app.post("/api/auth/login")
def login(payload: AuthPayload):
    result = db.authenticate_user(payload.username.strip(), payload.password)
    if not result:
        raise HTTPException(status_code=401, detail="invalid username or password")
    return result


def _resolve_owner(x_auth_token: Optional[str]) -> Optional[str]:
    if not x_auth_token:
        return None
    return db.get_user_by_token(x_auth_token)


# ---------- documents ----------

@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    x_auth_token: Optional[str] = Header(None, alias="X-Auth-Token"),
):
    owner_username = _resolve_owner(x_auth_token)
    document_id = f"doc_{uuid.uuid4().hex[:8]}"

    if ocr_engine.is_available():
        # Real OCR path (USE_REAL_OCR=true + model loaded successfully).
        # Image is deskewed/denoised/contrast-normalized before OCR, then
        # the raw decoded text is mapped into the same human-readable
        # field shape as the mocked fixtures (falls back to a single
        # "Raw OCR Text" field if nothing matched a known label).
        image_bytes = await file.read()
        try:
            fields = ocr_engine.run_ocr_and_map_fields(image_bytes)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"OCR failed: {exc}")

        overall_confidence = (
            sum(f["confidence"] for f in fields) / len(fields) if fields else 0.5
        )
        review_required = True  # real OCR output always needs human review
        record = db.create_document(
            document_id=document_id,
            filename=file.filename,
            fields=fields,
            overall_confidence=round(overall_confidence, 2),
            review_required=review_required,
            status="pending_review",
            owner_username=owner_username,
        )
        return record

    # Mocked path (default) — deterministic fixture keyed by filename.
    await asyncio.sleep(random.uniform(1.2, 2.5))

    fixture = pick_fixture(file.filename)
    confidences = [f["confidence"] for f in fixture["fields"]]
    overall_confidence = round(sum(confidences) / len(confidences), 2)
    review_required = fixture["review_required"]

    record = db.create_document(
        document_id=document_id,
        filename=file.filename,
        fields=fixture["fields"],
        overall_confidence=overall_confidence,
        review_required=review_required,
        status="pending_review" if review_required else "auto_approved",
        owner_username=owner_username,
    )
    return record


@app.get("/api/ocr-status")
def ocr_status():
    return {
        "use_real_ocr_flag": ocr_engine.USE_REAL_OCR,
        "model_available": ocr_engine.is_available(),
        "load_error": ocr_engine.get_load_error(),
    }


@app.get("/api/documents")
def list_documents(
    status: Optional[str] = None,
    x_auth_token: Optional[str] = Header(None, alias="X-Auth-Token"),
    mine: bool = False,
):
    owner_username = _resolve_owner(x_auth_token) if mine else None
    return {"documents": db.list_documents(status=status, owner_username=owner_username)}


@app.get("/api/documents/{document_id}")
def get_document(document_id: str):
    doc = db.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    return doc


# ---------- dummy plot upload + government records (for judge demo / AI-accuracy review) ----------

class DummyUploadPayload(BaseModel):
    plot_id: int


@app.post("/api/documents/dummy-upload")
def dummy_upload(payload: DummyUploadPayload):
    fixture = get_dummy_fixture(payload.plot_id)
    if not fixture:
        raise HTTPException(status_code=404, detail="unknown plot_id — expected 1-4")

    confidences = [f["confidence"] for f in fixture["fields"]]
    overall_confidence = round(sum(confidences) / len(confidences), 2)
    review_required = fixture["review_required"]

    document_id = f"doc_{uuid.uuid4().hex[:8]}"
    record = db.create_document(
        document_id=document_id,
        filename=f"dummy_plot_{payload.plot_id}.jpg",
        fields=fixture["fields"],
        overall_confidence=overall_confidence,
        review_required=review_required,
        status="pending_review" if review_required else "auto_approved",
        plot_id=str(payload.plot_id),
    )
    return record


@app.get("/api/government-records")
def list_govt_records():
    return {"records": government_records.list_government_records()}


@app.get("/api/government-records/{plot_id}")
def get_govt_record(plot_id: int):
    record = government_records.get_government_record(plot_id)
    if not record:
        raise HTTPException(status_code=404, detail="unknown plot_id — expected 1-4")
    return record


@app.post("/api/documents/{document_id}/approve")
def approve_document(document_id: str):
    doc = db.update_status(document_id, "approved")
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    return doc


class FieldUpdate(BaseModel):
    name: str
    label: str
    value: str
    confidence: float = 1.0  # manually corrected by a human reviewer — treat as high-confidence


class UpdateFieldsPayload(BaseModel):
    fields: List[FieldUpdate]


@app.post("/api/documents/{document_id}/fields")
def update_document_fields(document_id: str, payload: UpdateFieldsPayload):
    """Let a reviewer manually correct AI-extracted field values instead
    of only being able to approve-as-is or reject outright."""
    if not payload.fields:
        raise HTTPException(status_code=422, detail="at least one field is required")
    fields = [f.model_dump() for f in payload.fields]
    doc = db.update_fields(document_id, fields)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    return doc


class RejectPayload(BaseModel):
    reason: str


@app.post("/api/documents/{document_id}/reject")
def reject_document(document_id: str, payload: RejectPayload):
    if not payload.reason.strip():
        raise HTTPException(status_code=422, detail="a rejection reason is required")
    doc = db.reject_document(document_id, payload.reason.strip())
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    return doc


class BlacklistPayload(BaseModel):
    reason: str
    flagged_by: Optional[str] = None


@app.post("/api/documents/{document_id}/blacklist")
def blacklist_document(document_id: str, payload: BlacklistPayload):
    if not payload.reason.strip():
        raise HTTPException(status_code=422, detail="a reason is required to flag this document")
    entry = db.create_blacklist_entry(document_id, payload.reason.strip(), payload.flagged_by)
    if not entry:
        raise HTTPException(status_code=404, detail="document not found")
    return entry


@app.get("/api/blacklist")
def list_blacklist(resolved: Optional[bool] = None):
    return {"entries": db.list_blacklist_entries(resolved=resolved)}


class ResolveBlacklistPayload(BaseModel):
    resolution: str  # "dismissed" | "document_rejected"
    resolved_by: Optional[str] = None


@app.post("/api/blacklist/{entry_id}/resolve")
def resolve_blacklist(entry_id: str, payload: ResolveBlacklistPayload):
    if payload.resolution not in ("dismissed", "document_rejected"):
        raise HTTPException(status_code=422, detail="resolution must be 'dismissed' or 'document_rejected'")
    entry = db.resolve_blacklist_entry(entry_id, payload.resolution, payload.resolved_by)
    if not entry:
        raise HTTPException(status_code=404, detail="blacklist entry not found")
    if payload.resolution == "document_rejected":
        db.reject_document(entry["document_id"], f"Rejected via blacklist review: {entry['reason']}")
    return entry


class BoundaryPayload(BaseModel):
    points: List[List[float]]


@app.post("/api/documents/{document_id}/boundary")
def save_boundary(document_id: str, payload: BoundaryPayload):
    if len(payload.points) < 3:
        raise HTTPException(status_code=422, detail="boundary needs at least 3 points")
    doc = db.save_boundary(document_id, payload.points)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    return doc
