import json
import time
from loguru import logger
from src.storage.db import init_db, seed_signals
from src.scheduler.manager import scheduler_manager
from src.scheduler.tasks import run_scraping, run_scoring, run_enrichment, run_outreach, run_inbox_monitoring


def load_config():
    with open("scoring_config.json", "r") as f:
        return json.load(f)

def main():
    logger.add("logs/app.log", rotation="10 MB")
    logger.info("Starting Outbound Prospecting Agent...")

    # 1. Initialize Infrastructure
    init_db()
    
    # 2. Seed configuration
    config = load_config()
    seed_signals(config)

    # 3. Setup Scheduler
    # Discovery/Scraping: every 60 minutes
    scheduler_manager.add_job(run_scraping, interval_minutes=60, job_id="scraping_task")
    
    # Scoring: every 30 minutes
    scheduler_manager.add_job(run_scoring, interval_minutes=30, job_id="scoring_task")
    
    # Enrichment: every 45 minutes
    scheduler_manager.add_job(run_enrichment, interval_minutes=45, job_id="enrichment_task")
    
    # Outreach: every 120 minutes
    scheduler_manager.add_job(run_outreach, interval_minutes=120, job_id="outreach_task")
    
    # 5. Inbox Monitor: every 15 minutes
    scheduler_manager.add_job(run_inbox_monitoring, interval_minutes=15, job_id="inbox_monitor_task")


    # 4. Start Scheduler
    scheduler_manager.start()

    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler_manager.stop()
        logger.info("Agent stopped.")

if __name__ == "__main__":
    main()
