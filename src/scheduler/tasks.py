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

def run_enrichment():
    """Task to enrich companies with risk signals and find decision makers."""
    logger.info(f"[{datetime.now()}] Starting enrichment task...")
    
    # 1. Risk and Compliance Enrichment
    enricher = RiskComplianceEnricher()
    enricher.run(force=False) # Only process new ones by default
    
    # 2. People Discovery
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
