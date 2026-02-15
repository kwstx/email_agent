import json
import time
from loguru import logger
from src.storage.db import init_db, seed_signals
from src.scheduler.manager import scheduler_manager
from src.scheduler.tasks import (
    # Core pipeline tasks
    run_scraping, run_scoring, run_enrichment,
    run_outreach, run_inbox_monitoring, run_compliance_sync,
    # Step 15: Continuous expansion & refinement tasks
    run_outcome_tracking, run_scoring_refinement,
    run_rescoring, run_discovery_expansion,
    run_pipeline_health_check, run_full_pipeline_cycle,
)
from migrate_db import migrate_db


def load_config():
    with open("scoring_config.json", "r") as f:
        return json.load(f)

def main():
    logger.add("logs/app.log", rotation="10 MB")
    logger.info("Starting Outbound Prospecting Agent v2.0 (Self-Sustaining Mode)...")

    # 1. Initialize Infrastructure
    init_db()
    migrate_db()
    
    # 2. Seed configuration
    config = load_config()
    seed_signals(config)

    # ===================================================================
    # 3. CORE PIPELINE TASKS (existing)
    # ===================================================================
    
    # Discovery/Scraping: every 60 minutes
    scheduler_manager.add_job(run_scraping, interval_minutes=60, job_id="scraping_task")
    
    # Scoring: every 30 minutes
    scheduler_manager.add_job(run_scoring, interval_minutes=30, job_id="scoring_task")
    
    # Enrichment: every 45 minutes
    scheduler_manager.add_job(run_enrichment, interval_minutes=45, job_id="enrichment_task")
    
    # Outreach: every 120 minutes
    scheduler_manager.add_job(run_outreach, interval_minutes=120, job_id="outreach_task")
    
    # Inbox Monitor: every 15 minutes
    scheduler_manager.add_job(run_inbox_monitoring, interval_minutes=15, job_id="inbox_monitor_task")

    # Compliance Sync: every 60 minutes
    scheduler_manager.add_job(run_compliance_sync, interval_minutes=60, job_id="compliance_sync_task")

    # ===================================================================
    # 4. CONTINUOUS EXPANSION & REFINEMENT TASKS (Step 15)
    # ===================================================================

    # Outcome Tracking: every 6 hours — analyze reply rates per signal/tier
    scheduler_manager.add_job(run_outcome_tracking, interval_minutes=360, job_id="outcome_tracking_task")

    # Scoring Refinement: every 24 hours — adjust ICP weights based on outcomes
    scheduler_manager.add_job(run_scoring_refinement, interval_minutes=1440, job_id="scoring_refinement_task")

    # Re-scoring: every 12 hours — re-score companies if model changed or data is stale
    scheduler_manager.add_job(run_rescoring, interval_minutes=720, job_id="rescoring_task")

    # Discovery Expansion: every 24 hours — generate new queries from winning leads
    scheduler_manager.add_job(run_discovery_expansion, interval_minutes=1440, job_id="discovery_expansion_task")

    # Pipeline Health Check: every 2 hours — detect bottlenecks and alert
    scheduler_manager.add_job(run_pipeline_health_check, interval_minutes=120, job_id="pipeline_health_task")

    # Full Pipeline Cycle: every 24 hours — complete end-to-end orchestration
    scheduler_manager.add_job(run_full_pipeline_cycle, interval_minutes=1440, job_id="full_pipeline_cycle_task")

    # ===================================================================
    # 5. Start the Engine
    # ===================================================================
    logger.info("Scheduler configured with 12 recurring tasks:")
    logger.info("  Core:   scraping(60m) | scoring(30m) | enrichment(45m) | outreach(120m) | inbox(15m) | compliance(60m)")
    logger.info("  Refine: outcomes(6h) | weight_refine(24h) | rescore(12h) | expand(24h) | health(2h) | full_cycle(24h)")

    scheduler_manager.start()

    # Run an initial pipeline health check on startup
    try:
        logger.info("Running initial pipeline health check...")
        run_pipeline_health_check()
    except Exception as e:
        logger.warning(f"Initial health check failed (non-fatal): {e}")

    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler_manager.stop()
        logger.info("Agent stopped.")

if __name__ == "__main__":
    main()
