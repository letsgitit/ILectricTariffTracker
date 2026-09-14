"""Runs a check on one or all tracked documents: fetch -> extract -> diff -> store."""
from __future__ import annotations

import datetime as dt
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models import TrackedDocument, Snapshot, ChangeEvent
from app.fetcher import fetch_document
from app.extractor import extract_line_items

logger = logging.getLogger("tariff_tracker.checker")


def check_document(session: Session, doc: TrackedDocument) -> Snapshot:
    result = fetch_document(doc.url, doc.doc_type)

    snapshot = Snapshot(
        tracked_document_id=doc.id,
        fetched_at=dt.datetime.utcnow(),
        http_status=result.http_status,
        fetch_error=result.error,
    )

    if result.error:
        logger.warning("Fetch failed for %s (%s): %s", doc.name, doc.url, result.error)
        snapshot.content_hash = ""
        snapshot.raw_text_excerpt = ""
        snapshot.parsed_line_items = {}
        session.add(snapshot)
        session.commit()
        return snapshot

    snapshot.content_hash = result.content_hash
    snapshot.raw_text_excerpt = result.text[:5000]
    snapshot.parsed_line_items = extract_line_items(result.text, doc.line_item_patterns)

    previous = doc.latest_snapshot()  # most recent snapshot BEFORE this one is added
    session.add(snapshot)
    session.commit()  # commit so snapshot.id exists for the ChangeEvent FK

    if previous and previous.content_hash and previous.content_hash != snapshot.content_hash:
        line_item_diffs = _diff_line_items(previous.parsed_line_items or {}, snapshot.parsed_line_items or {})
        if line_item_diffs:
            change_type = "line_item"
            summary = f"{len(line_item_diffs)} tracked line item(s) changed in {doc.name}"
        else:
            change_type = "content_hash"
            summary = (
                f"Document content changed for {doc.name} "
                f"(no configured line-item patterns caught a specific value — review manually)"
            )
        event = ChangeEvent(
            tracked_document_id=doc.id,
            detected_at=dt.datetime.utcnow(),
            previous_snapshot_id=previous.id,
            new_snapshot_id=snapshot.id,
            change_type=change_type,
            summary=summary,
            line_item_diffs=line_item_diffs,
        )
        session.add(event)
        session.commit()
        logger.info("CHANGE DETECTED: %s", summary)

    return snapshot


def _diff_line_items(old: dict, new: dict) -> dict:
    diffs = {}
    for label, new_val in new.items():
        old_val = old.get(label)
        if new_val is not None and old_val is not None and str(new_val) != str(old_val):
            diffs[label] = {"old": old_val, "new": new_val}
    return diffs


def check_all_documents(session: Session, only_doc_key: Optional[str] = None):
    query = session.query(TrackedDocument).filter_by(active=True)
    if only_doc_key:
        query = query.filter_by(doc_key=only_doc_key)
    docs = query.all()
    results = []
    for doc in docs:
        results.append(check_document(session, doc))
    return results
