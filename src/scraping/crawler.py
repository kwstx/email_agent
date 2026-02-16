import asyncio
import aiohttp
import re
import json
from typing import List, Dict, Set, Optional
from bs4 import BeautifulSoup
from loguru import logger
from urllib.parse import urljoin, urlparse
from sqlmodel import select
from datetime import datetime

from src.storage.db import get_session
from src.storage.models import Company, Signal, CompanySignalLink

class WebCrawler:
    """Crawler to visit high-signal pages and extract content."""
    
    def __init__(self, config_path: str = "scoring_config.json", max_pages_per_domain: int = 10, timeout: int = 30):
        self.max_pages_per_domain = max_pages_per_domain
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }
        
        # Load scoring config for signal detection
        with open(config_path, "r") as f:
            self.config = json.load(f)
            
        # High-signal path patterns for crawling
        self.signal_patterns = {
            "docs": re.compile(r"docs|documentation|developer|api", re.I),
            "security": re.compile(r"security|trust|compliance|privacy", re.I),
            "blog": re.compile(r"blog|news", re.I),
            "careers": re.compile(r"careers|jobs|hiring", re.I),
            "product": re.compile(r"product|features|solutions|platform", re.I),
            "pricing": re.compile(r"pricing|plans", re.I),
            "smb_signal": re.compile(r"book a demo|meet the founders", re.I),
            "enterprise_signal": re.compile(r"investor relations|esg report|global locations|procurement", re.I),
        }

    async def _fetch(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        try:
            async with session.get(url, headers=self.headers, timeout=self.timeout, allow_redirects=True) as response:
                if response.status == 200:
                    return await response.text()
                logger.warning(f"Failed to fetch {url}: Status {response.status}")
                return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def _extract_text(self, html: str) -> str:
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove scripts and styles
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
            
        # Get text, clean up whitespace
        text = soup.get_text(separator=" ")
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        return " ".join(chunk for chunk in chunks if chunk)

    def _find_signal_links(self, html: str, base_url: str) -> Dict[str, str]:
        links = {}
        if not html:
            return links
            
        soup = BeautifulSoup(html, "html.parser")
        domain = urlparse(base_url).netloc
        
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(base_url, href)
            
            # Ensure it's internal
            if urlparse(full_url).netloc != domain:
                continue
                
            path = urlparse(full_url).path.lower()
            text = a.get_text().lower()
            
            for key, pattern in self.signal_patterns.items():
                if key not in links and (pattern.search(path) or pattern.search(text)):
                    links[key] = full_url
        
        return links

    async def scrape_company(self, company_domain: str) -> Dict[str, str]:
        """Scrapes high-signal pages for a given domain."""
        base_url = f"https://{company_domain}"
        if not base_url.startswith("http"):
            base_url = "https://" + base_url
            
        logger.info(f"Scraping company: {company_domain}")
        pages_content = {}
        
        async with aiohttp.ClientSession() as session:
            # 1. Scrape Homepage
            homepage_html = await self._fetch(session, base_url)
            if not homepage_html:
                # Try http if https fails
                base_url = base_url.replace("https://", "http://")
                homepage_html = await self._fetch(session, base_url)
                
            if not homepage_html:
                logger.error(f"Could not reach {company_domain}")
                return {}
                
            pages_content["homepage"] = self._extract_text(homepage_html)
            
            # 2. Find high-signal links
            signal_links = self._find_signal_links(homepage_html, base_url)
            logger.info(f"Found {len(signal_links)} signal links for {company_domain}")
            
            # 3. Scrape signal links
            tasks = []
            keys = []
            for key, url in signal_links.items():
                if key != "homepage": # already scraped
                    tasks.append(self._fetch(session, url))
                    keys.append(key)
            
            if tasks:
                results = await asyncio.gather(*tasks)
                for key, html in zip(keys, results):
                    if html:
                        pages_content[key] = self._extract_text(html)
                        
        return pages_content

    def consolidate_profile(self, pages_content: Dict[str, str]) -> str:
        """Combines all page text into a single unified profile."""
        profile_parts = []
        for key, text in pages_content.items():
            profile_parts.append(f"--- {key.upper()} ---")
            profile_parts.append(text)
            profile_parts.append("\n")
        
        return "\n".join(profile_parts)

    async def run(self):
        """Main entry point to scrape all unscraped companies."""
        with get_session() as session:
            statement = select(Company).where(Company.is_scraped == False)
            companies = session.exec(statement).all()
            
            if not companies:
                logger.info("No new companies to scrape.")
                return

            logger.info(f"Found {len(companies)} companies to scrape.")
            
            for company in companies:
                try:
                    pages_content = await self.scrape_company(company.domain)
                    if pages_content:
                        profile = self.consolidate_profile(pages_content)
                        company.website_content = profile
                        company.is_scraped = True
                        
                        # Add a snippet to description if missing
                        if not company.description and "homepage" in pages_content:
                            snippet = pages_content["homepage"][:500] + "..."
                            company.description = snippet
                            
                        session.add(company)
                        session.commit()
                        logger.success(f"Successfully scraped {company.domain}")
                    else:
                        # Mark as scraped even if failed to avoid infinite retries
                        company.is_scraped = True
                        session.add(company)
                        session.commit()
                        logger.warning(f"Scraped {company.domain} but found no content.")
                except Exception as e:
                    logger.error(f"Failed to process {company.domain}: {e}")
                    session.rollback()

if __name__ == "__main__":
    crawler = WebCrawler()
    asyncio.run(crawler.run())
