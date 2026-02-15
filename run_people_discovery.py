import asyncio
from src.storage.db import get_session
from src.storage.models import Company, Contact
from sqlmodel import select
from src.enrichment.people_discovery import PeopleDiscoverer

def setup_test_data():
    with get_session() as session:
        # Find a company to test with
        company = session.exec(select(Company).limit(1)).first()
        if company:
            print(f"Setting {company.domain} to high_fit for testing.")
            company.fitness_level = "high_fit"
            session.add(company)
            session.commit()
            return company.domain
        else:
            print("No companies found.")
            return None

async def run():
    domain = setup_test_data()
    if not domain:
        return

    discoverer = PeopleDiscoverer()
    await discoverer.run()
    
    with get_session() as session:
        contacts = session.exec(select(Contact)).all()
        print(f"Total contacts found: {len(contacts)}")
        for c in contacts:
            print(f"- {c.name} ({c.title}) Score: {c.relevance_score}")

if __name__ == "__main__":
    asyncio.run(run())
