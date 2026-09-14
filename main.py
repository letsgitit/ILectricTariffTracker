"""Illinois Electric Tariff Tracker API.

Tracks ComEd and Ameren Illinois C&I regulatory tariff line items and checks
weekly for changes. See README.md for deployment instructions.
"""
from __future__ import annotations

import datetime as dt
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import init_db, SessionLocal
from app.models import TrackedDocument, Snapshot, ChangeEvent
from app.config import sync_tracked_documents_from_config
from app.checker import check_all_documents, check_document
from app.scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="IL Electric Tariff Tracker",
    description="Tracks ComEd & Ameren Illinois C&I regulatory tariff line items weekly.",
    version="1.0.0",
)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@app.on_event("startup")
def on_startup():
    init_db()
    sync_tracked_documents_from_config()
    start_scheduler()


# ---------- Response models ----------

class DocumentOut(BaseModel):
    id: int
    doc_key: str
    utility: str
    rate_class: str
    name: str
    url: str
    doc_type: str
    notes: str
    active: bool

    class Config:
        from_attributes = True


class SnapshotOut(BaseModel):
    id: int
    fetched_at: dt.datetime
    content_hash: str
    http_status: Optional[int]
    parsed_line_items: dict
    fetch_error: Optional[str]

    class Config:
        from_attributes = True


class ChangeEventOut(BaseModel):
    id: int
    tracked_document_id: int
    detected_at: dt.datetime
    change_type: str
    summary: str
    line_item_diffs: dict

    class Config:
        from_attributes = True


class NewDocumentIn(BaseModel):
    doc_key: str
    utility: str
    rate_class: str
    name: str
    url: str
    doc_type: str = "pdf"
    notes: str = ""
    line_item_patterns: list = []


# ---------- Routes ----------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/documents", response_model=list[DocumentOut])
def list_documents(utility: Optional[str] = None, session: Session = Depends(get_session)):
    q = session.query(TrackedDocument).filter_by(active=True)
    if utility:
        q = q.filter(TrackedDocument.utility.ilike(f"%{utility}%"))
    return q.all()


@app.post("/documents", response_model=DocumentOut)
def add_document(doc: NewDocumentIn, session: Session = Depends(get_session)):
    existing = session.query(TrackedDocument).filter_by(doc_key=doc.doc_key).one_or_none()
    if existing:
        raise HTTPException(400, f"doc_key '{doc.doc_key}' already exists")
    record = TrackedDocument(**doc.model_dump(), active=True)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


@app.get("/documents/{doc_key}/current", response_model=SnapshotOut)
def current_snapshot(doc_key: str, session: Session = Depends(get_session)):
    doc = session.query(TrackedDocument).filter_by(doc_key=doc_key).one_or_none()
    if not doc:
        raise HTTPException(404, "document not found")
    snap = doc.latest_snapshot()
    if not snap:
        raise HTTPException(404, "no snapshots yet — run a check first")
    return snap


@app.get("/documents/{doc_key}/history", response_model=list[SnapshotOut])
def snapshot_history(doc_key: str, session: Session = Depends(get_session)):
    doc = session.query(TrackedDocument).filter_by(doc_key=doc_key).one_or_none()
    if not doc:
        raise HTTPException(404, "document not found")
    return doc.snapshots


@app.post("/documents/{doc_key}/check-now", response_model=SnapshotOut)
def check_now(doc_key: str, session: Session = Depends(get_session)):
    doc = session.query(TrackedDocument).filter_by(doc_key=doc_key).one_or_none()
    if not doc:
        raise HTTPException(404, "document not found")
    return check_document(session, doc)


@app.post("/check-all", response_model=list[SnapshotOut])
def check_all(session: Session = Depends(get_session)):
    return check_all_documents(session)


@app.get("/changes", response_model=list[ChangeEventOut])
def list_changes(since: Optional[dt.date] = None, session: Session = Depends(get_session)):
    q = session.query(ChangeEvent).order_by(ChangeEvent.detected_at.desc())
    if since:
        q = q.filter(ChangeEvent.detected_at >= since)
    return q.all()
