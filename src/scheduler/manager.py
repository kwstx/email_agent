from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
import time

class TaskScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False

    def add_job(self, func, interval_minutes, job_id, **kwargs):
        """Add a recurring job to the scheduler."""
        logger.info(f"Adding job: {job_id} with interval {interval_minutes}m")
        self.scheduler.add_job(
            func,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id=job_id,
            replace_existing=True,
            **kwargs
        )

    def start(self):
        """Start the scheduler."""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            logger.success("Task scheduler started.")

    def stop(self):
        """Stop the scheduler."""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Task scheduler stopped.")

# Instance to be used across the app
scheduler_manager = TaskScheduler()
