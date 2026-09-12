"""SQLite persistence layer for the land-record digitizer (mocked-demo tier).

Two tables:
- documents: everything /api/analyze produces plus review-workflow state
  (status, boundary) and an owner_username FK so uploaders can find their
  own past documents.
- users: uploader accounts (separate from the Gov Employee Portal, which
  still uses mocked sessionStorage-only auth — this is real, persisted,
  password-hashed accounts for the public-facing upload user).
"""
import hashlib
import json
import os
import secrets
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import create_engine, Column, String, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DB_PATH = os.path.join(os.path.dirname(__file__), "land_records.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    username = Column(String, primary_key=True)
    password_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    token = Column(String, nullable=True)  # current session token, demo-simple (no expiry)


class Document(Base):
    __tablename__ = "documents"

    document_id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    processed_at = Column(DateTime, nullable=False)
    fields_json = Column(Text, nullable=False)  # JSON-encoded list[dict]
    overall_confidence = Column(Float, nullable=False)
    review_required = Column(Boolean, nullable=False)
    status = Column(String, nullable=False)
    boundary_json = Column(Text, nullable=True)  # JSON-encoded list[[x,y]] or null
    owner_username = Column(String, ForeignKey("users.username"), nullable=True)
    plot_id = Column(String, nullable=True)  # links to a dummy plot (1-4) for gov-record comparison
    rejection_reason = Column(Text, nullable=True)  # set when status == "rejected"
    fields_edited_by_reviewer = Column(Boolean, nullable=False, default=False)


class BlacklistEntry(Base):
    """A flag raised against a document (bad AI output or bad user upload)
    for an admin to review separately from the normal reviewer queue."""

    __tablename__ = "blacklist_entries"

    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.document_id"), nullable=False)
    reason = Column(Text, nullable=False)
    flagged_by = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False)
    resolved = Column(Boolean, nullable=False, default=False)
    resolution = Column(String, nullable=True)  # "dismissed" | "document_rejected"
    resolved_by = Column(String, nullable=True)
    resolved_at = Column(DateTime, nullable=True)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    return SessionLocal()


# ---------- password hashing (demo-grade: salted SHA-256, not bcrypt/argon2) ----------

def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


# ---------- users ----------

def create_user(username: str, password: str) -> Optional[dict]:
    db = get_session()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            return None
        salt = secrets.token_hex(8)
        token = secrets.token_hex(16)
        user = User(
            username=username,
            password_hash=_hash_password(password, salt),
            salt=salt,
            token=token,
        )
        db.add(user)
        db.commit()
        return {"username": username, "token": token}
    finally:
        db.close()


def authenticate_user(username: str, password: str) -> Optional[dict]:
    db = get_session()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return None
        if _hash_password(password, user.salt) != user.password_hash:
            return None
        token = secrets.token_hex(16)
        user.token = token
        db.commit()
        return {"username": username, "token": token}
    finally:
        db.close()


def get_user_by_token(token: str) -> Optional[str]:
    db = get_session()
    try:
        user = db.query(User).filter(User.token == token).first()
        return user.username if user else None
    finally:
        db.close()


# ---------- documents ----------

def _row_to_dict(row: Document) -> dict:
    return {
        "document_id": row.document_id,
        "filename": row.filename,
        "processed_at": row.processed_at.replace(tzinfo=timezone.utc).isoformat(),
        "fields": json.loads(row.fields_json),
        "overall_confidence": row.overall_confidence,
        "review_required": row.review_required,
        "status": row.status,
        "boundary": json.loads(row.boundary_json) if row.boundary_json else None,
        "owner_username": row.owner_username,
        "plot_id": row.plot_id,
        "rejection_reason": row.rejection_reason,
        "fields_edited_by_reviewer": row.fields_edited_by_reviewer,
    }


def create_document(
    document_id: str,
    filename: str,
    fields: list,
    overall_confidence: float,
    review_required: bool,
    status: str,
    owner_username: Optional[str] = None,
    plot_id: Optional[str] = None,
) -> dict:
    db = get_session()
    try:
        row = Document(
            document_id=document_id,
            filename=filename,
            processed_at=datetime.now(timezone.utc).replace(tzinfo=None),
            fields_json=json.dumps(fields),
            overall_confidence=overall_confidence,
            review_required=review_required,
            status=status,
            boundary_json=None,
            owner_username=owner_username,
            plot_id=plot_id,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _row_to_dict(row)
    finally:
        db.close()


def list_documents(status: Optional[str] = None, owner_username: Optional[str] = None) -> List[dict]:
    db = get_session()
    try:
        query = db.query(Document)
        if status:
            query = query.filter(Document.status == status)
        if owner_username:
            query = query.filter(Document.owner_username == owner_username)
        rows = query.order_by(Document.processed_at.desc()).all()
        return [_row_to_dict(r) for r in rows]
    finally:
        db.close()


def get_document(document_id: str) -> Optional[dict]:
    db = get_session()
    try:
        row = db.query(Document).filter(Document.document_id == document_id).first()
        return _row_to_dict(row) if row else None
    finally:
        db.close()


def update_status(document_id: str, status: str) -> Optional[dict]:
    db = get_session()
    try:
        row = db.query(Document).filter(Document.document_id == document_id).first()
        if not row:
            return None
        row.status = status
        db.commit()
        db.refresh(row)
        return _row_to_dict(row)
    finally:
        db.close()


def save_boundary(document_id: str, points: list) -> Optional[dict]:
    db = get_session()
    try:
        row = db.query(Document).filter(Document.document_id == document_id).first()
        if not row:
            return None
        row.boundary_json = json.dumps(points)
        row.status = "boundary_drawn"
        db.commit()
        db.refresh(row)
        return _row_to_dict(row)
    finally:
        db.close()


def reject_document(document_id: str, reason: str) -> Optional[dict]:
    db = get_session()
    try:
        row = db.query(Document).filter(Document.document_id == document_id).first()
        if not row:
            return None
        row.status = "rejected"
        row.rejection_reason = reason
        db.commit()
        db.refresh(row)
        return _row_to_dict(row)
    finally:
        db.close()


def update_fields(document_id: str, fields: list) -> Optional[dict]:
    """Let a reviewer manually correct one or more AI-extracted field
    values (e.g. when the AI misread text but a full reject is overkill).
    Replaces the fields list wholesale and marks the document as having
    been manually edited by a reviewer."""
    db = get_session()
    try:
        row = db.query(Document).filter(Document.document_id == document_id).first()
        if not row:
            return None
        row.fields_json = json.dumps(fields)
        row.fields_edited_by_reviewer = True
        db.commit()
        db.refresh(row)
        return _row_to_dict(row)
    finally:
        db.close()


# ---------- blacklist (flag a document's AI output or upload for admin review) ----------

def _blacklist_entry_to_dict(row: BlacklistEntry) -> dict:
    return {
        "id": row.id,
        "document_id": row.document_id,
        "reason": row.reason,
        "flagged_by": row.flagged_by,
        "created_at": row.created_at.replace(tzinfo=timezone.utc).isoformat(),
        "resolved": row.resolved,
        "resolution": row.resolution,
        "resolved_by": row.resolved_by,
        "resolved_at": row.resolved_at.replace(tzinfo=timezone.utc).isoformat() if row.resolved_at else None,
    }


def create_blacklist_entry(document_id: str, reason: str, flagged_by: Optional[str] = None) -> Optional[dict]:
    db = get_session()
    try:
        doc = db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            return None
        entry = BlacklistEntry(
            id=f"flag_{secrets.token_hex(6)}",
            document_id=document_id,
            reason=reason,
            flagged_by=flagged_by,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            resolved=False,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return _blacklist_entry_to_dict(entry)
    finally:
        db.close()


def list_blacklist_entries(resolved: Optional[bool] = None) -> List[dict]:
    db = get_session()
    try:
        query = db.query(BlacklistEntry)
        if resolved is not None:
            query = query.filter(BlacklistEntry.resolved == resolved)
        rows = query.order_by(BlacklistEntry.created_at.desc()).all()
        return [_blacklist_entry_to_dict(r) for r in rows]
    finally:
        db.close()


def resolve_blacklist_entry(entry_id: str, resolution: str, resolved_by: Optional[str] = None) -> Optional[dict]:
    db = get_session()
    try:
        row = db.query(BlacklistEntry).filter(BlacklistEntry.id == entry_id).first()
        if not row:
            return None
        row.resolved = True
        row.resolution = resolution
        row.resolved_by = resolved_by
        row.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        db.refresh(row)
        return _blacklist_entry_to_dict(row)
    finally:
        db.close()
