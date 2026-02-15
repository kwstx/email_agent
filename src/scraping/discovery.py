import re
from typing import List, Set, Dict
from urllib.parse import urlparse
from googlesearch import search
from loguru import logger
from tqdm import tqdm
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from src.storage.db import get_session
from src.storage.models import Company

class DiscoverySource:
    """Base class for all discovery sources."""
    def discover(self) -> List[Dict[str, str]]:
        raise NotImplementedError("Subclasses must implement discover()")

class SearchEngineSource(DiscoverySource):
    """Discovers companies using Google Search queries."""
    
    def __init__(self, queries: List[str], num_results: int = 20):
        self.queries = queries
        self.num_results = num_results
        self.excluded_domains = {
            'linkedin.com', 'twitter.com', 'facebook.com', 'instagram.com',
            'youtube.com', 'medium.com', 'github.com', 'reddit.com',
            'crunchbase.com', 'glassdoor.com', 'indeed.com', 'ycombinator.com',
            'producthunt.com', 'softwarereviews.com', 'g2.com', 'capterra.com',
            'trustradius.com', 'wikipedia.org'
        }

    def _extract_domain(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return ""

    def discover(self) -> List[Dict[str, str]]:
        discovered = []
        unique_domains = set()

        for query in self.queries:
            logger.info(f"Searching for: {query}")
            try:
                # Using googlesearch-python
                results = search(query, num_results=self.num_results)
                for url in results:
                    logger.debug(f"Found URL: {url}")
                    domain = self._extract_domain(url)
                    if domain and domain not in self.excluded_domains and domain not in unique_domains:
                        # Basic assumption: the domain is the company website
                        # We might need better name extraction later
                        name = domain.split('.')[0].capitalize()
                        discovered.append({"name": name, "domain": domain})
                        unique_domains.add(domain)
            except Exception as e:
                logger.error(f"Error searching for '{query}': {e}")
        
        return discovered

class ManualListSource(DiscoverySource):
    """Source for hardcoded or pre-discovered company lists."""
    def __init__(self, leads: List[Dict[str, str]]):
        self.leads = leads
    
    def discover(self) -> List[Dict[str, str]]:
        return self.leads

class DiscoveryEngine:
    """Orchestrates discovery from multiple sources and saves to DB."""
    
    def __init__(self):
        self.sources: List[DiscoverySource] = []

    def add_source(self, source: DiscoverySource):
        self.sources.append(source)

    def run(self):
        logger.info("Starting discovery process...")
        total_new = 0
        
        for source in self.sources:
            try:
                results = source.discover()
                logger.info(f"Source {source.__class__.__name__} found {len(results)} potential leads.")
                
                with get_session() as session:
                    for lead in tqdm(results, desc=f"Saving leads from {source.__class__.__name__}"):
                        try:
                            # Normalize domain
                            domain = lead['domain'].lower().strip()
                            if domain.startswith(('http://', 'https://')):
                                parsed = urlparse(domain)
                                domain = parsed.netloc
                            if domain.startswith('www.'):
                                domain = domain[4:]
                            
                            # Check if already exists
                            statement = select(Company).where(Company.domain == domain)
                            existing = session.exec(statement).first()
                            
                            if not existing:
                                company = Company(
                                    name=lead['name'],
                                    domain=domain,
                                    is_scraped=False
                                )
                                session.add(company)
                                session.commit()
                                total_new += 1
                        except IntegrityError:
                            session.rollback()
                        except Exception as e:
                            logger.error(f"Error saving lead {lead.get('domain')}: {e}")
                            session.rollback()
            except Exception as e:
                logger.error(f"Source {source.__class__.__name__} failed: {e}")
        
        logger.success(f"Discovery complete. Added {total_new} new companies to the database.")
        return total_new

if __name__ == "__main__":
    from src.storage.db import init_db
    
    # Ensure DB is initialized
    init_db()

    # Starter leads from our research (Directories, Partner pages, etc.)
    manual_leads = [
        # AI Agent Platforms
        {"name": "Lindy", "domain": "lindy.ai"},
        {"name": "Spell", "domain": "spell.so"},
        {"name": "Fixie", "domain": "fixie.ai"},
        {"name": "Lyzr", "domain": "lyzr.ai"},
        {"name": "Enso", "domain": "enso.bot"},
        {"name": "Dify", "domain": "dify.ai"},
        {"name": "CrewAI", "domain": "crewai.com"},
        {"name": "Decagon", "domain": "decagon.ai"},
        {"name": "Emergence", "domain": "emergence.ai"},
        
        # Enterprise AI & Infrastructure
        {"name": "Cohere", "domain": "cohere.com"},
        {"name": "Kore.ai", "domain": "kore.ai"},
        {"name": "Aisera", "domain": "aisera.com"},
        {"name": "Brainbase", "domain": "brainbase.com"},
        {"name": "Gumloop", "domain": "gumloop.com"},
        {"name": "Tines", "domain": "tines.com"},
        
        # Anthropic Partners/Customers
        {"name": "Mintlify", "domain": "mintlify.com"},
        {"name": "Vibecode", "domain": "vibecode.com"},
        {"name": "Greptile", "domain": "greptile.com"},
        {"name": "Carta Healthcare", "domain": "carta.healthcare"},
        {"name": "Binti", "domain": "binti.com"},
        {"name": "Workato", "domain": "workato.com"},
        
        # Emerging Startups
        {"name": "Brance", "domain": "brance.ai"},
        {"name": "ToothFairyAI", "domain": "toothfairy.ai"},
        {"name": "Enhans", "domain": "enhans.ai"},
        {"name": "Yuma", "domain": "yuma.ai"},
        {"name": "Bilic", "domain": "bilic.ai"},
        {"name": "Naratix", "domain": "naratix.ai"}
    ]

    engine = DiscoveryEngine()
    
    # Add manual source for immediate results
    engine.add_source(ManualListSource(manual_leads))
    
    # Add automated search source
    queries = [
        "AI agent orchestration platform startups",
        "LLM governance and security platforms",
        "generative AI security startups 2025",
        "autonomous AI agents for enterprise automation",
        "site:ycombinator.com 'AI agent' 2024",
        "site:producthunt.com 'AI agents' top",
        "AI agents conference speakers 2024"
    ]
    engine.add_source(SearchEngineSource(queries, num_results=15))
    
    # Run the discovery
    try:
        new_leads = engine.run()
        print(f"Success! Added {new_leads} new leads.")
    except Exception as e:
        logger.error(f"Discovery engine failed: {e}")
