import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db import SessionLocal
from app.checker import check_all_documents

logger = logging.getLogger("tariff_tracker.scheduler")

# Default: every Monday at 06:00 server time. Override via env vars if you
# want a different cadence — e.g. TARIFF_CHECK_DAY=wed TARIFF_CHECK_HOUR=3
CHECK_DAY = os.environ.get("TARIFF_CHECK_DAY", "mon")
CHECK_HOUR = int(os.environ.get("TARIFF_CHECK_HOUR", "6"))


def run_scheduled_check():
    logger.info("Starting scheduled weekly tariff check")
    session = SessionLocal()
    try:
        results = check_all_documents(session)
        logger.info("Weekly check complete: %d documents checked", len(results))
    finally:
        session.close()


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_scheduled_check,
        trigger=CronTrigger(day_of_week=CHECK_DAY, hour=CHECK_HOUR),
        id="weekly_tariff_check",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started: weekly check on %s at %02d:00", CHECK_DAY, CHECK_HOUR)
    return scheduler
