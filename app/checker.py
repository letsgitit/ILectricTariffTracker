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

    # Last *successful* snapshot: a failed fetch in between (hash "") must not
    # hide a change that happened during the outage.
    previous = (
        session.query(Snapshot)
        .filter(Snapshot.tracked_document_id == doc.id, Snapshot.content_hash != "")
        .order_by(Snapshot.fetched_at.desc(), Snapshot.id.desc())
        .first()
    )
    session.add(snapshot)
    session.commit()  # commit so snapshot.id exists for the ChangeEvent FK

    if previous and previous.content_hash and previous.content_hash != snapshot.content_hash:
        line_item_diffs = _diff_line_items(previous.parsed_line_items or {}, snapshot.parsed_line_items or {})
        if line_item_diffs:
            change_type = "line_item"
            summary = f"{len(line_item_diffs)} tracked line item(s) changed in {doc.name}"
            lost = [k for k, v in line_item_diffs.items() if v["new"] is None]
            if lost:
                summary += (
                    f" ({len(lost)} no longer matched — pattern may need updating "
                    f"after a layout change)"
                )
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
    """Labels whose value differs between snapshots. A value appearing
    (None -> x) or disappearing (x -> None, e.g. a pattern broken by a layout
    change) counts as a difference; None -> None does not."""
    diffs = {}
    for label in {**old, **new}:
        old_val, new_val = old.get(label), new.get(label)
        if old_val != new_val:
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
