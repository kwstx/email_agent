import asyncio
import aiohttp
import re
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup
from loguru import logger
from urllib.parse import urljoin, urlparse
from sqlmodel import select, Session

from src.storage.db import get_session
from src.storage.models import Company, Contact

class PeopleDiscoverer:
    """
    Discovers relevant stakeholders (decision makers) within qualified companies.
    Focuses on technical and security leadership roles.
    """
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }
        
        # Team page patterns
        self.team_page_patterns = [
            "/team", "/about", "/about-us", "/company", "/people", "/leadership", "/our-team"
        ]
        
        # Role definition and scoring
        self.role_patterns = {
            # C-Level (High Priority)
            "CTO": 10,
            "Chief Technology Officer": 10,
            "CISO": 10,
            "Chief Information Security Officer": 10,
            "CIO": 9,
            "Chief Information Officer": 9,
            "Chief Product Officer": 9,
            "CPO": 9,
            "Chief Data Officer": 9,
            "CDO": 9,
            # VP Level
            "VP of Engineering": 8,
            "Vice President of Engineering": 8,
            "VP Engineering": 8,
            "VP of Security": 8,
            "Vice President of Security": 8,
            "VP Security": 8,
            "VP of Product": 7,
            "Vice President of Product": 7,
            "VP Product": 7,
            "VP of AI": 8,
            "Vice President of AI": 8,
            "Head of Engineering": 8,
            "Head of Security": 8,
            "Head of Infrastructure": 7,
            "Head of AI": 8,
            # Director Level
            "Director of Engineering": 6,
            "Director of Security": 6,
            "Director of Platform": 6,
            "Director of Infrastructure": 6,
            "Director of AI": 6,
            # Other Key Roles
            "Security Architect": 5,
            "Platform Engineer": 4,
            "Principal Engineer": 5,
            "Staff Engineer": 4,
            "Engineering Manager": 4,
            "Product Manager": 3,
        }
        
    async def _fetch(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        try:
            async with session.get(url, headers=self.headers, timeout=self.timeout, allow_redirects=True) as response:
                if response.status == 200:
                    return await response.text()
                # logger.warning(f"Failed to fetch {url}: Status {response.status}")
                return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def _find_team_links(self, html: str, base_url: str) -> List[str]:
        """Finds potential team/about pages from the homepage."""
        links = []
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
            
            for pattern in self.team_page_patterns:
                if pattern in path or pattern in text:
                    links.append(full_url)
                    break
        
        return list(set(links))

    def _extract_contacts_from_html(self, html: str, company_id: int) -> List[Contact]:
        """Parses HTML to find people and titles."""
        contacts = []
        if not html:
            return contacts
            
        soup = BeautifulSoup(html, "html.parser")
        
        # Strategy 1: Look for elements containing title keywords
        # and try to find the associated name.
        
        # We'll use a simplified approach:
        # Find all block elements (div, li, p, h1-h6)
        # Check if they contain a title.
        
        candidates = []
        
        # Helper to clean text
        def clean(text):
            return " ".join(text.split()).strip()

        # Find all elements that might be a person card
        # Heuristic: Container with small amount of text, potentially an image?
        # Actually, let's search for the titles first.
        
        for text_node in soup.find_all(string=True):
            clean_text = clean(text_node)
            if not clean_text:
                continue
                
            # Check if this text matches a known title
            matched_title = None
            matched_score = 0
            
            for role, score in self.role_patterns.items():
                if role.lower() in clean_text.lower():
                    # Check if it's a good match (not just a substring of something unrelated)
                    # For now simple containment.
                    if len(clean_text) < 100: # Title shouldn't be too long
                        if score > matched_score:
                            matched_score = score
                            matched_title = role # Use the canonical role name or the text?
                            # Use text but clean it up? Or canonical?
                            # Use the text found if it's short, else canonical
                            matched_title = clean_text if len(clean_text) < 50 else role

            if matched_title:
                # We found a title. Now find the name.
                # Look at previous siblings or parent's previous siblings.
                parent = text_node.parent
                
                # Search nearby for name
                name = None
                
                # Check previous sibling element
                prev = parent.find_previous_sibling()
                if prev:
                    prev_text = clean(prev.get_text())
                    if 3 < len(prev_text) < 30 and prev_text[0].isupper():
                        name = prev_text
                
                # Check parent's previous sibling (common in grid layouts: <div>Name</div><div>Title</div>)
                if not name:
                    parent_prev = parent.parent.find_previous_sibling() if parent.parent else None
                    if parent_prev: # careful here
                        pass # complicated logic, skipping for simplicity
                        
                # Check for Heading tags nearby
                if not name:
                    # Look for the nearest preceding H tag
                    h_tag = parent.find_previous(["h1", "h2", "h3", "h4", "h5", "h6"])
                    if h_tag:
                        h_text = clean(h_tag.get_text())
                        if 3 < len(h_text) < 30:
                            name = h_text
                            
                # Strategy 2: Check for LinkedIn links nearby
                linkedin_url = None
                # Search within the same container (go up 2-3 levels)
                container = parent
                for _ in range(3):
                    if not container or container.name == "body":
                        break
                    
                    link = container.find("a", href=re.compile(r"linkedin\.com/in/"))
                    if link:
                        linkedin_url = link["href"]
                        # Sometimes the name IS the link text
                        link_text = clean(link.get_text())
                        if not name and 3 < len(link_text) < 30 and "linkedin" not in link_text.lower():
                            name = link_text
                        break
                    container = container.parent
                
                if name and matched_title:
                    # Verify name looks like a name (at least 2 words, no numbers)
                    if " " in name and not any(char.isdigit() for char in name):
                        # Create contact
                        contact = Contact(
                            company_id=company_id,
                            name=name,
                            title=matched_title,
                            linkedin_url=linkedin_url,
                            outreach_status="pending",
                            relevance_score=matched_score
                        )
                        contacts.append((contact, matched_score))

        return contacts

    def _deduplicate_contacts(self, contacts_with_score: List[Tuple[Contact, int]]) -> List[Contact]:
        """Deduplicates based on name and keeps highest score/most complete info."""
        unique = {}
        for contact, score in contacts_with_score:
            key = contact.name.lower()
            if key not in unique:
                unique[key] = (contact, score)
            else:
                existing_contact, existing_score = unique[key]
                # Update if new one has better score or more info (e.g. linkedin)
                if score > existing_score:
                    unique[key] = (contact, score)
                elif not existing_contact.linkedin_url and contact.linkedin_url:
                    unique[key] = (contact, score)
        
        # Sort by score descending
        sorted_contacts = sorted(unique.values(), key=lambda x: x[1], reverse=True)
        return [c for c, _ in sorted_contacts]

    async def run(self):
        """Scrapes team pages for qualified companies."""
        with get_session() as session:
            # 1. Get qualified companies (e.g., fitness_level='high_fit')
            # For now, let's just create contacts for any scraped company to test, 
            # OR strictly follow "surpasses ICP threshold".
            # Let's assume threshold is stored in fitness_level or we use score.
            # Using fitness_level='high_fit' as per previous prompt implications.
            
            statement = select(Company).where(Company.fitness_level == "high_priority")
            companies = session.exec(statement).all()
            
            if not companies:
                logger.info("No high-fit companies found to discover people for.")
                return

            logger.info(f"Found {len(companies)} high-fit companies for people discovery.")
            
            async with aiohttp.ClientSession() as http_session:
                for company in companies:
                    logger.info(f"Discovering people for {company.name} ({company.domain})...")
                    
                    # 1. Scrape Homepage to find subpages if we haven't stored them,
                    # or just guess standard paths.
                    base_url = f"https://{company.domain}"
                    homepage_html = await self._fetch(http_session, base_url)
                    
                    if not homepage_html:
                        logger.warning(f"Could not access {base_url} for people discovery")
                        continue
                        
                    team_links = self._find_team_links(homepage_html, base_url)
                    logger.info(f"Found {len(team_links)} potential team pages: {team_links}")
                    
                    # Include homepage itself as some stick team there
                    pages_to_scan = [base_url] + team_links
                    
                    all_found_contacts = []
                    
                    for url in pages_to_scan:
                        logger.info(f"Scanning {url}...")
                        html = await self._fetch(http_session, url)
                        if html:
                            found = self._extract_contacts_from_html(html, company.id)
                            all_found_contacts.extend(found)
                    
                    # Deduplicate and Rank
                    final_contacts = self._deduplicate_contacts(all_found_contacts)
                    
                    logger.success(f"Found {len(final_contacts)} unique relevant contacts for {company.name}")
                    
                    # Save to DB
                    for contact in final_contacts:
                        # Check if exists
                        existing = session.exec(
                            select(Contact).where(Contact.company_id == company.id).where(Contact.name == contact.name)
                        ).first()
                        
                        if not existing:
                            session.add(contact)
                            logger.info(f"Added contact: {contact.name} - {contact.title}")
                        else:
                            # Update title or linkedin if missing
                            if not existing.linkedin_url and contact.linkedin_url:
                                existing.linkedin_url = contact.linkedin_url
                                session.add(existing)
                                logger.info(f"Updated contact: {contact.name}")
                    
                    session.commit()

if __name__ == "__main__":
    discoverer = PeopleDiscoverer()
    asyncio.run(discoverer.run())
