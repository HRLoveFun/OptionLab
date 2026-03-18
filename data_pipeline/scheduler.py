import os
import logging
from datetime import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .data_service import DataService

logger = logging.getLogger(__name__)


def _parse_time_env(var: str, default: str) -> tuple[int, int]:
    """Parse HH:MM from an env var, return (hour, minute)."""
    raw = os.environ.get(var, default).strip()
    parts = raw.split(":")
    return int(parts[0]), int(parts[1])


class UpdateScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone=os.environ.get("SCHED_TZ", "UTC"))

    def start_daily_update(self, tickers: list[str]):
        hour, minute = _parse_time_env("SCHED_DAILY_TIME", "16:15")
        trigger = CronTrigger(hour=hour, minute=minute)

        def job():
            for t in tickers:
                try:
                    DataService.manual_update(t, days=7)
                    logger.info(f"Auto-updated {t}")
                except Exception as e:
                    logger.exception(f"Auto-update failed for {t}: {e}")

        self.scheduler.add_job(job, trigger, id="daily_auto_update", replace_existing=True)
        self.scheduler.start()

    def start_monthly_correlation_update(self, tickers: list[str]):
        """Schedule monthly correlation data update at the beginning of each month.

        This ensures correlation charts are updated with the latest data monthly.
        The job runs at 2:00 AM on the 1st of each month.
        """
        day = int(os.environ.get("SCHED_MONTHLY_DAY", "1"))
        hour, minute = _parse_time_env("SCHED_MONTHLY_TIME", "02:00")
        trigger = CronTrigger(day=day, hour=hour, minute=minute)

        def correlation_job():
            for t in tickers:
                try:
                    # Trigger a full data update which includes correlation recalculation
                    DataService.manual_update(t, days=30)
                    logger.info(f"Monthly correlation update completed for {t}")
                except Exception as e:
                    logger.exception(f"Monthly correlation update failed for {t}: {e}")

        self.scheduler.add_job(
            correlation_job,
            trigger,
            id="monthly_correlation_update",
            replace_existing=True
        )

        # Start scheduler if not already running
        if not self.scheduler.running:
            self.scheduler.start()

        logger.info(f"Monthly correlation update scheduled for tickers: {tickers}")

    def shutdown(self):
        self.scheduler.shutdown(wait=False)
