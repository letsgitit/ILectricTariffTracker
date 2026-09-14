#!/usr/bin/env python3
"""Run a one-off check of all tracked documents.

Use this if you'd rather drive the weekly check with an external cron job
or scheduled task (e.g. a host crontab, a cloud scheduler job) instead of
the in-process APScheduler that runs inside the API container.

Usage:
    python scripts/run_check_now.py            # check all documents
    python scripts/run_check_now.py comed-rate-rds   # check just one
"""
import sys
import logging

sys.path.insert(0, "/app")  # match the Docker WORKDIR; adjust if run elsewhere

from app.db import init_db, SessionLocal
from app.config import sync_tracked_documents_from_config
from app.checker import check_all_documents

logging.basicConfig(level=logging.INFO)


def main():
    init_db()
    sync_tracked_documents_from_config()
    only_key = sys.argv[1] if len(sys.argv) > 1 else None
    session = SessionLocal()
    try:
        results = check_all_documents(session, only_doc_key=only_key)
        for snap in results:
            status = "ERROR: " + snap.fetch_error if snap.fetch_error else "OK"
            print(f"[{snap.tracked_document_id}] {status}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
