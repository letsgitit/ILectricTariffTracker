import os
import yaml

from app.db import SessionLocal
from app.models import TrackedDocument

CONFIG_PATH = os.environ.get(
    "TARIFF_CONFIG_PATH", "/app/config/tracked_documents.yaml"
)


def load_seed_documents(path: str = CONFIG_PATH):
    with open(path, "r") as f:
        return yaml.safe_load(f) or []


def sync_tracked_documents_from_config(path: str = CONFIG_PATH):
    """Upsert tracked documents from the YAML config into the DB.

    Safe to call on every startup: existing docs (matched by doc_key) are
    updated in place, new ones are inserted, nothing is deleted (so manual
    additions/edits made via the API survive a redeploy).
    """
    session = SessionLocal()
    try:
        entries = load_seed_documents(path)
        for entry in entries:
            doc_key = entry["id"]
            existing = (
                session.query(TrackedDocument)
                .filter_by(doc_key=doc_key)
                .one_or_none()
            )
            fields = dict(
                utility=entry["utility"],
                rate_class=entry["rate_class"],
                name=entry["name"],
                url=entry["url"],
                doc_type=entry.get("doc_type", "pdf"),
                notes=entry.get("notes", ""),
                line_item_patterns=entry.get("line_item_patterns", []),
            )
            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
            else:
                session.add(TrackedDocument(doc_key=doc_key, active=True, **fields))
        session.commit()
    finally:
        session.close()
