import asyncio
import glob
import os
import random
import threading
import time
import uuid
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import db
import government_records
import ocr_engine
from dummy_plot_fixtures import get_dummy_fixture
from fixtures import pick_fixture
from logging_config import get_logger

logger = get_logger(__name__)

app = FastAPI(title="Land Record Digitizer — Mock API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Every request in, one line: method, path, status, timing. This is
    the "processing log" you see scroll by in the terminal for every
    upload/click, on top of the more detailed logs at each endpoint."""
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - start) * 1000
    logger.info(
        "%s %s -> %d (%.0fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.on_event("startup")
def on_startup():
    db.init_db()
    logger.info("database initialized")
    # Preload the TrOCR model in the background if AI review might be
    # used, so the first per-upload "AI review" request isn't stuck
    # waiting ~30s+ for a cold model load. Best-effort — failures are
    # surfaced via /api/ocr-status, not raised at startup.
    if os.getenv("PRELOAD_TROCR", "false").lower() in ("1", "true", "yes"):
        logger.info("PRELOAD_TROCR set — loading TrOCR model in background thread")

        def _preload():
            ready = ocr_engine.is_model_ready()
            if ready:
                logger.info("TrOCR model loaded and ready")
            else:
                logger.warning("TrOCR model failed to load: %s", ocr_engine.get_load_error())

        threading.Thread(target=_preload, daemon=True).start()


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
    use_ai: bool = Form(False),
    x_auth_token: Optional[str] = Header(None, alias="X-Auth-Token"),
):
    owner_username = _resolve_owner(x_auth_token)
    document_id = f"doc_{uuid.uuid4().hex[:8]}"
    logger.info(
        "analyze: doc=%s filename=%s use_ai=%s owner=%s",
        document_id, file.filename, use_ai, owner_username or "anonymous",
    )

    # Per-upload toggle: the user explicitly chooses "AI review" (real
    # TrOCR) vs "Saved responses" (mocked, deterministic fixtures) on
    # each upload, independent of the server-wide USE_REAL_OCR flag.
    want_ai = use_ai or ocr_engine.USE_REAL_OCR
    if want_ai and ocr_engine.is_model_ready():
        # Real OCR path. Image is deskewed/denoised/contrast-normalized
        # before OCR, then the raw decoded text is mapped into the same
        # human-readable field shape as the mocked fixtures (falls back
        # to a single "Raw OCR Text" field if nothing matched a known
        # label).
        image_bytes = await file.read()
        logger.info("analyze: doc=%s running real TrOCR on %d bytes", document_id, len(image_bytes))
        start = time.monotonic()
        try:
            fields = ocr_engine.run_ocr_and_map_fields(image_bytes)
        except Exception as exc:
            logger.error("analyze: doc=%s OCR failed: %s", document_id, exc)
            raise HTTPException(status_code=500, detail=f"OCR failed: {exc}")
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(
            "analyze: doc=%s OCR done in %.0fms, %d field(s) extracted",
            document_id, elapsed_ms, len(fields),
        )

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
            source="ai_review",
        )
        return record

    if want_ai and not ocr_engine.is_model_ready():
        # User asked for AI review but the model isn't loaded/available —
        # fail loudly instead of silently falling back, so the toggle
        # behaves predictably.
        logger.warning("analyze: doc=%s AI review requested but model unavailable: %s", document_id, ocr_engine.get_load_error())
        raise HTTPException(
            status_code=503,
            detail=f"AI review unavailable: {ocr_engine.get_load_error() or 'model not loaded'}",
        )

    # Mocked path (default) — deterministic fixture keyed by filename.
    await asyncio.sleep(random.uniform(1.2, 2.5))

    fixture = pick_fixture(file.filename)
    confidences = [f["confidence"] for f in fixture["fields"]]
    overall_confidence = round(sum(confidences) / len(confidences), 2)
    review_required = fixture["review_required"]
    logger.info(
        "analyze: doc=%s saved-response fixture matched, overall_confidence=%.2f review_required=%s",
        document_id, overall_confidence, review_required,
    )

    record = db.create_document(
        document_id=document_id,
        filename=file.filename,
        fields=fixture["fields"],
        overall_confidence=overall_confidence,
        review_required=review_required,
        status="pending_review" if review_required else "auto_approved",
        owner_username=owner_username,
        source="saved_response",
    )
    return record


@app.get("/api/ocr-status")
def ocr_status():
    return {
        "use_real_ocr_flag": ocr_engine.USE_REAL_OCR,
        "model_available": ocr_engine.is_model_ready(),
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
    use_ai: bool = False


DUMMY_SCAN_DIR = os.path.join(os.path.dirname(__file__), "dummy_scans")


@app.post("/api/documents/dummy-upload")
def dummy_upload(payload: DummyUploadPayload):
    fixture = get_dummy_fixture(payload.plot_id)
    if not fixture:
        raise HTTPException(status_code=404, detail="unknown plot_id — expected 1-4")

    document_id = f"doc_{uuid.uuid4().hex[:8]}"
    logger.info("dummy_upload: doc=%s plot_id=%s use_ai=%s", document_id, payload.plot_id, payload.use_ai)

    want_ai = payload.use_ai or ocr_engine.USE_REAL_OCR
    if want_ai and ocr_engine.is_model_ready():
        # Run real OCR on the actual generated scan for this plot instead
        # of returning the static mocked fixture — same "AI review" path
        # as a real upload. TrOCR is a single-line model, so the demo
        # scan is pre-split into one image per field/line (plot_N_lineK.png);
        # each line is OCR'd separately and the results combined, then
        # mapped the same way as any other AI-review upload (baked-in
        # text mirrors the mocked fixture, including plots 3/4's
        # deliberately seeded errors, so results stay comparable).
        line_paths = sorted(glob.glob(os.path.join(DUMMY_SCAN_DIR, f"plot_{payload.plot_id}_line*.png")))
        if not line_paths:
            raise HTTPException(status_code=500, detail=f"dummy scan images missing for plot {payload.plot_id}")
        try:
            line_bytes = []
            for p in line_paths:
                with open(p, "rb") as f:
                    line_bytes.append(f.read())
            fields = ocr_engine.run_ocr_multiline_and_map_fields(line_bytes)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"OCR failed: {exc}")

        overall_confidence = (
            sum(f["confidence"] for f in fields) / len(fields) if fields else 0.5
        )
        record = db.create_document(
            document_id=document_id,
            filename=f"dummy_plot_{payload.plot_id}.jpg",
            fields=fields,
            overall_confidence=round(overall_confidence, 2),
            review_required=True,
            status="pending_review",
            plot_id=str(payload.plot_id),
            source="ai_review",
        )
        return record

    if want_ai and not ocr_engine.is_model_ready():
        raise HTTPException(
            status_code=503,
            detail=f"AI review unavailable: {ocr_engine.get_load_error() or 'model not loaded'}",
        )

    confidences = [f["confidence"] for f in fixture["fields"]]
    overall_confidence = round(sum(confidences) / len(confidences), 2)
    review_required = fixture["review_required"]

    record = db.create_document(
        document_id=document_id,
        filename=f"dummy_plot_{payload.plot_id}.jpg",
        fields=fixture["fields"],
        overall_confidence=overall_confidence,
        review_required=review_required,
        status="pending_review" if review_required else "auto_approved",
        plot_id=str(payload.plot_id),
        source="saved_response",
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
    logger.info("approve: doc=%s approved by reviewer", document_id)
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
    logger.info("update_fields: doc=%s reviewer corrected %d field(s)", document_id, len(fields))
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
    logger.info("reject: doc=%s rejected, reason=%r", document_id, payload.reason.strip())
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
    logger.info("blacklist: doc=%s flagged by=%s reason=%r", document_id, payload.flagged_by, payload.reason.strip())
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
    logger.info("resolve_blacklist: entry=%s resolution=%s resolved_by=%s", entry_id, payload.resolution, payload.resolved_by)
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
    logger.info("save_boundary: doc=%s saved with %d point(s)", document_id, len(payload.points))
    return doc
