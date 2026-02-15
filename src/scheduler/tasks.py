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

def run_enrichment():
    """Task to find decision makers for high-fit companies."""
    logger.info(f"[{datetime.now()}] Starting enrichment task...")
    # Logic will go in src/enrichment
    pass

def run_outreach():
    """Task to send outreach emails."""
    logger.info(f"[{datetime.now()}] Starting outreach task...")
    # Logic will go in src/outreach
    pass
