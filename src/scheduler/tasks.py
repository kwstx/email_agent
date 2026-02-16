from loguru import logger
from datetime import datetime

import asyncio
from src.scraping.crawler import WebCrawler

def run_scraping():
    """Task to discover and scrape new companies."""
    logger.info(f"[{datetime.now()}] Starting scraping task...")
    crawler = WebCrawler()
    asyncio.run(crawler.run())

from src.scoring.detector import AgentSignalDetector

def run_scoring():
    """Task to score scraped companies."""
    logger.info(f"[{datetime.now()}] Starting scoring task...")
    detector = AgentSignalDetector()
    detector.run()

from src.enrichment.risk_compliance import RiskComplianceEnricher
from src.enrichment.people_discovery import PeopleDiscoverer
from src.enrichment.size_verification import SizeVerificationEnricher

def run_enrichment():
    """Task to enrich companies with risk signals and find decision makers."""
    logger.info(f"[{datetime.now()}] Starting enrichment task...")
    
    # 1. Risk and Compliance Enrichment
    enricher = RiskComplianceEnricher()
    enricher.run(force=False) # Only process new ones by default
    
    # 2. Size Verification (Step 5)
    size_enricher = SizeVerificationEnricher()
    size_enricher.run(force=False)
    
    # 3. People Discovery
    discoverer = PeopleDiscoverer()
    asyncio.run(discoverer.run())

from src.outreach.generator import OutreachManager

def run_outreach():
    """Task to send outreach emails."""
    logger.info(f"[{datetime.now()}] Starting outreach task...")
    manager = OutreachManager()
    manager.run()

from src.outreach.inbox_monitor import InboxMonitor

def run_inbox_monitoring():
    """Task to check inbox for replies."""
    logger.info(f"[{datetime.now()}] Starting inbox monitoring...")
    try:
        monitor = InboxMonitor()
        monitor.process_inbox()
    except Exception as e:
        logger.error(f"Inbox monitoring failed: {e}")

from src.compliance.suppression import SuppressionManager
from src.storage.db import get_session

def run_compliance_sync():
    """Task to sync suppression list and audit compliance state."""
    logger.info(f"[{datetime.now()}] Starting compliance sync...")
    try:
        manager = SuppressionManager()
        with get_session() as session:
            count = manager.sync_from_contacts(session)
            stats = manager.get_suppression_stats(session)
            session.commit()
        logger.info(f"Compliance sync complete: {count} new suppressions. Stats: {stats}")
    except Exception as e:
        logger.error(f"Compliance sync failed: {e}")


# ===================================================================
# STEP 15: CONTINUOUS EXPANSION & REFINEMENT TASKS
# ===================================================================

def run_outcome_tracking():
    """Task to analyze outreach outcomes and log performance metrics."""
    logger.info(f"[{datetime.now()}] Starting outcome tracking...")
    try:
        from src.feedback.outcome_tracker import OutcomeTracker
        tracker = OutcomeTracker()
        report = tracker.log_report()
        logger.success(f"Outcome tracking complete. Global reply rate: {report['global_stats']['reply_rate_pct']}%")
    except Exception as e:
        logger.error(f"Outcome tracking failed: {e}")


def run_scoring_refinement():
    """Task to refine ICP scoring weights based on outreach outcomes."""
    logger.info(f"[{datetime.now()}] Starting scoring refinement...")
    try:
        from src.feedback.scoring_refiner import ScoringRefiner
        refiner = ScoringRefiner()
        summary = refiner.refine(dry_run=False)
        logger.success(
            f"Scoring refinement complete. "
            f"{summary['changes_count']} weight adjustments made. "
            f"Threshold adjusted: {summary['threshold_adjusted']}"
        )
    except Exception as e:
        logger.error(f"Scoring refinement failed: {e}")


def run_rescoring():
    """Task to re-score companies when the model has been updated."""
    logger.info(f"[{datetime.now()}] Starting re-scoring check...")
    try:
        from src.feedback.rescoring_engine import RescoringEngine
        engine = RescoringEngine()

        # First check if model was updated (by scoring refiner)
        model_changed = engine.rescore_if_model_updated()

        # Also re-score stale companies (>7 days since last score)
        if not model_changed:
            engine.rescore_stale(days_threshold=7)
    except Exception as e:
        logger.error(f"Re-scoring failed: {e}")


def run_discovery_expansion():
    """Task to generate new discovery queries from successful lead patterns."""
    logger.info(f"[{datetime.now()}] Starting discovery expansion...")
    try:
        from src.feedback.discovery_expander import DiscoveryExpander
        from src.scraping.discovery import DiscoveryEngine, SearchEngineSource

        # Generate new queries
        expander = DiscoveryExpander()
        new_queries = expander.generate_expansion_queries()

        if new_queries:
            logger.info(f"Generated {len(new_queries)} expansion queries. Running discovery...")
            engine = DiscoveryEngine()
            engine.add_source(SearchEngineSource(new_queries, num_results=10))
            new_leads = engine.run()
            logger.success(f"Discovery expansion complete. Added {new_leads} new companies.")
        else:
            logger.info("No new expansion queries generated.")
    except Exception as e:
        logger.error(f"Discovery expansion failed: {e}")


def run_pipeline_health_check():
    """Task to check pipeline health and log alerts."""
    logger.info(f"[{datetime.now()}] Starting pipeline health check...")
    try:
        from src.feedback.pipeline_monitor import PipelineHealthMonitor
        monitor = PipelineHealthMonitor()
        report = monitor.log_health_report()
        monitor.save_report(report)

        # Log critical alerts prominently
        critical_alerts = [a for a in report.get("alerts", []) if a["level"] == "critical"]
        if critical_alerts:
            logger.error(f"PIPELINE HEALTH: {len(critical_alerts)} critical alert(s) detected!")
    except Exception as e:
        logger.error(f"Pipeline health check failed: {e}")


def run_full_pipeline_cycle():
    """
    Full pipeline orchestration: runs the entire end-to-end pipeline in sequence.
    
    Order: Discovery → Scraping → Scoring → Enrichment → Outreach → Inbox → Compliance
    
    This is the master task that ensures all stages run in the correct order.
    Useful for initial bootstrapping or when you want a guaranteed full cycle.
    """
    logger.info(f"[{datetime.now()}] ========== FULL PIPELINE CYCLE START ==========")
    
    stages = [
        ("1. Discovery Expansion", run_discovery_expansion),
        ("2. Scraping", run_scraping),
        ("3. Scoring", run_scoring),
        ("4. Enrichment", run_enrichment),
        ("5. Outreach", run_outreach),
        ("6. Inbox Monitoring", run_inbox_monitoring),
        ("7. Compliance Sync", run_compliance_sync),
        ("8. Outcome Tracking", run_outcome_tracking),
        ("9. Pipeline Health", run_pipeline_health_check),
    ]

    results = {}
    for stage_name, task_fn in stages:
        try:
            logger.info(f"--- {stage_name} ---")
            task_fn()
            results[stage_name] = "success"
        except Exception as e:
            logger.error(f"{stage_name} failed: {e}")
            results[stage_name] = f"failed: {e}"

    logger.info(f"[{datetime.now()}] ========== FULL PIPELINE CYCLE COMPLETE ==========")
    for stage, status in results.items():
        logger.info(f"  {stage}: {status}")

    return results
