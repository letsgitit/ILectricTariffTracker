"""HTTP API for the tariff tracker. See README for the endpoint list."""
from __future__ import annotations

import datetime as dt
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.checker import check_all_documents
from app.config import sync_tracked_documents_from_config
from app.db import SessionLocal, init_db
from app.models import ChangeEvent, Snapshot, TrackedDocument
from app.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    sync_tracked_documents_from_config()
    scheduler = start_scheduler()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Illinois Electric Tariff Tracker", lifespan=lifespan)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class DocumentIn(BaseModel):
    doc_key: str
    utility: str
    rate_class: str
    name: str
    url: str
    doc_type: str = "pdf"
    notes: str = ""
    line_item_patterns: list[dict] = []


def _doc_out(d: TrackedDocument) -> dict:
    return {
        "doc_key": d.doc_key, "utility": d.utility, "rate_class": d.rate_class,
        "name": d.name, "url": d.url, "doc_type": d.doc_type, "notes": d.notes,
        "line_item_patterns": d.line_item_patterns, "active": d.active,
    }


def _snapshot_out(s: Snapshot) -> dict:
    return {
        "id": s.id, "fetched_at": s.fetched_at, "http_status": s.http_status,
        "content_hash": s.content_hash, "parsed_line_items": s.parsed_line_items,
        "fetch_error": s.fetch_error, "raw_text_excerpt": s.raw_text_excerpt,
    }


def _get_doc(session: Session, doc_key: str) -> TrackedDocument:
    doc = session.query(TrackedDocument).filter_by(doc_key=doc_key).one_or_none()
    if not doc:
        raise HTTPException(404, f"Unknown document: {doc_key}")
    return doc


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/documents")
def list_documents(utility: Optional[str] = None, session: Session = Depends(get_session)):
    q = session.query(TrackedDocument)
    if utility:
        q = q.filter(TrackedDocument.utility == utility)
    return [_doc_out(d) for d in q.all()]


@app.post("/documents", status_code=201)
def add_document(body: DocumentIn, session: Session = Depends(get_session)):
    if session.query(TrackedDocument).filter_by(doc_key=body.doc_key).first():
        raise HTTPException(409, f"doc_key already exists: {body.doc_key}")
    doc = TrackedDocument(active=True, **body.model_dump())
    session.add(doc)
    session.commit()
    return _doc_out(doc)


@app.get("/documents/{doc_key}/current")
def current(doc_key: str, session: Session = Depends(get_session)):
    doc = _get_doc(session, doc_key)
    snap = doc.latest_snapshot()
    if not snap:
        raise HTTPException(404, "No snapshots yet — run a check first")
    return {**_doc_out(doc), "snapshot": _snapshot_out(snap)}


@app.get("/documents/{doc_key}/history")
def history(doc_key: str, session: Session = Depends(get_session)):
    doc = _get_doc(session, doc_key)
    return [_snapshot_out(s) for s in doc.snapshots]


@app.post("/documents/{doc_key}/check-now")
def check_now(doc_key: str, session: Session = Depends(get_session)):
    _get_doc(session, doc_key)
    snaps = check_all_documents(session, only_doc_key=doc_key)
    return [_snapshot_out(s) for s in snaps]


@app.post("/check-all")
def check_all(session: Session = Depends(get_session)):
    snaps = check_all_documents(session)
    return {"checked": len(snaps), "errors": sum(1 for s in snaps if s.fetch_error)}


@app.get("/changes")
def changes(since: Optional[dt.date] = None, session: Session = Depends(get_session)):
    q = session.query(ChangeEvent).order_by(ChangeEvent.detected_at.desc())
    if since:
        q = q.filter(ChangeEvent.detected_at >= dt.datetime.combine(since, dt.time.min))
    return [
        {
            "id": e.id, "tracked_document_id": e.tracked_document_id,
            "detected_at": e.detected_at, "change_type": e.change_type,
            "summary": e.summary, "line_item_diffs": e.line_item_diffs,
        }
        for e in q.all()
    ]
