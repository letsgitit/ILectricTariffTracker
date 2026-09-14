"""Database models for the tariff tracker.

Three tables:
  TrackedDocument - one row per tariff document we watch (seeded from config/tracked_documents.yaml)
  Snapshot        - one row per successful fetch of a document, with a content hash and any
                    parsed line-item values
  ChangeEvent     - one row per detected change between two consecutive snapshots
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class TrackedDocument(Base):
    __tablename__ = "tracked_document"

    id = Column(Integer, primary_key=True)
    doc_key = Column(String, unique=True, nullable=False)  # e.g. "comed-rate-rds"
    utility = Column(String, nullable=False)
    rate_class = Column(String, nullable=False)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    doc_type = Column(String, default="pdf")
    notes = Column(Text, default="")
    line_item_patterns = Column(JSON, default=list)  # [{"label": ..., "pattern": ...}]
    active = Column(Boolean, default=True)

    snapshots = relationship(
        "Snapshot", back_populates="document", order_by="Snapshot.fetched_at.desc()"
    )

    def latest_snapshot(self):
        return self.snapshots[0] if self.snapshots else None


class Snapshot(Base):
    __tablename__ = "snapshot"

    id = Column(Integer, primary_key=True)
    tracked_document_id = Column(Integer, ForeignKey("tracked_document.id"), nullable=False)
    fetched_at = Column(DateTime, default=dt.datetime.utcnow)
    content_hash = Column(String, nullable=False)
    http_status = Column(Integer)
    raw_text_excerpt = Column(Text)          # first ~5000 chars, for quick review
    parsed_line_items = Column(JSON, default=dict)   # {label: value}
    fetch_error = Column(Text, nullable=True)

    document = relationship("TrackedDocument", back_populates="snapshots")


class ChangeEvent(Base):
    __tablename__ = "change_event"

    id = Column(Integer, primary_key=True)
    tracked_document_id = Column(Integer, ForeignKey("tracked_document.id"), nullable=False)
    detected_at = Column(DateTime, default=dt.datetime.utcnow)
    previous_snapshot_id = Column(Integer, ForeignKey("snapshot.id"), nullable=True)
    new_snapshot_id = Column(Integer, ForeignKey("snapshot.id"), nullable=False)
    change_type = Column(String)  # "content_hash" or "line_item"
    summary = Column(Text)
    line_item_diffs = Column(JSON, default=dict)  # {label: {"old": x, "new": y}}
