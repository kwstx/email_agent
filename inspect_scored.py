from src.storage.db import get_session
from src.storage.models import Company
from sqlmodel import select

def inspect_companies():
    with get_session() as session:
        statement = select(Company).where(Company.is_scored == True).limit(20)
        companies = session.exec(statement).all()
        print(f"Scored companies: {len(companies)}")
        for c in companies:
            print(f"{c.domain} | Score: {c.fitness_score} | Level: {c.fitness_level!r}")

if __name__ == "__main__":
    inspect_companies()
