from src.storage.db import get_session
from src.storage.models import Company
from sqlmodel import select

def inspect_companies():
    with get_session() as session:
        statement = select(Company).limit(10)
        companies = session.exec(statement).all()
        print(f"Total companies checked: {len(companies)}")
        for c in companies:
            print(f"Domain: {c.domain}, Scored: {c.is_scored}, Score: {c.fitness_score}, Level: {c.fitness_level}")

if __name__ == "__main__":
    inspect_companies()
