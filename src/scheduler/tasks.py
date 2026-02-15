from loguru import logger
from datetime import datetime

def run_scraping():
    """Task to discover and scrape new companies."""
    logger.info(f"[{datetime.now()}] Starting scraping task...")
    # Logic will go in src/scraping
    pass

def run_scoring():
    """Task to score scraped companies."""
    logger.info(f"[{datetime.now()}] Starting scoring task...")
    # Logic will go in src/scoring
    pass

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
