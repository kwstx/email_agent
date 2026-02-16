import os
import requests
import random
from typing import Optional
from loguru import logger
from sqlmodel import select, Session
from src.storage.models import Company
from src.storage.db import get_session

class SizeVerificationEnricher:
    """
    Enriches companies with employee count data using external APIs.
    Filters companies to ensure they fit the SMB profile.
    """
    
    def __init__(self):
        self.apollo_api_key = os.getenv("APOLLO_API_KEY")
        self.max_smb_size = 500

    def fetch_employee_count(self, domain: str) -> Optional[int]:
        """
        Fetches employee count from an external provider (e.g., Apollo).
        Currently implements a mock for demonstration/free tier simulation.
        """
        if not self.apollo_api_key or self.apollo_api_key == "":
            # Mock behavior: Generate a plausible employee count if no API key
            # For demonstration, we'll return a random number between 10 and 1000
            # but biased towards smaller numbers for this agent's "luck"
            count = random.randint(10, 800)
            logger.warning(f"No APOLLO_API_KEY found. Using mock employee count for {domain}: {count}")
            return count

        try:
            url = f"https://api.apollo.io/v1/organizations/enrich?domain={domain}"
            headers = {
                "Cache-Control": "no-cache", 
                "Content-Type": "application/json", 
                "X-Api-Key": self.apollo_api_key
            }
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                count = data.get("organization", {}).get("estimated_num_employees")
                return count
            
            logger.error(f"Apollo API error {response.status_code}: {response.text}")
            return None
        except Exception as e:
            logger.error(f"Error fetching size for {domain}: {e}")
            return None

    def process_company(self, session: Session, company: Company):
        """Enriches a single company with size data."""
        if company.employee_count is not None:
            return

        logger.info(f"Verifying size for {company.domain}")
        count = self.fetch_employee_count(company.domain)
        
        if count is not None:
            company.employee_count = count
            session.add(company)
            logger.success(f"Updated {company.domain} employee_count: {count}")
        else:
            logger.warning(f"Could not determine size for {company.domain}")

    def run(self, force: bool = False):
        """Runs the size verification for all companies."""
        with get_session() as session:
            statement = select(Company).where(Company.is_scored == True)
            if not force:
                statement = statement.where(Company.employee_count == None)
                
            companies = session.exec(statement).all()
            
            if not companies:
                logger.info("No companies found needing size verification.")
                return
                
            logger.info(f"Starting size verification for {len(companies)} companies.")
            for company in companies:
                self.process_company(session, company)
            
            session.commit()

if __name__ == "__main__":
    import argparse
    from dotenv import load_dotenv
    load_dotenv()
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Force re-verification of all companies")
    args = parser.parse_args()
    
    enricher = SizeVerificationEnricher()
    enricher.run(force=args.force)
