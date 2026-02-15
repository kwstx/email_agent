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

def run_outreach():
    """Task to send outreach emails."""
    logger.info(f"[{datetime.now()}] Starting outreach task...")
    # Logic will go in src/outreach
    pass
