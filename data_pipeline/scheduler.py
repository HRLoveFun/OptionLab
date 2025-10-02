import os
import logging
from datetime import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .data_service import DataService

logger = logging.getLogger(__name__)


class UpdateScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone=os.environ.get("SCHED_TZ", "UTC"))

    def start_daily_update(self, tickers: list[str]):
        # 16:15 local time (scheduler timezone). Use cron.
        trigger = CronTrigger(hour=16, minute=15)

        def job():
            for t in tickers:
                try:
                    DataService.manual_update(t, days=7)
                    logger.info(f"Auto-updated {t}")
                except Exception as e:
                    logger.exception(f"Auto-update failed for {t}: {e}")

        self.scheduler.add_job(job, trigger, id="daily_auto_update", replace_existing=True)
        self.scheduler.start()

    def shutdown(self):
        self.scheduler.shutdown(wait=False)
