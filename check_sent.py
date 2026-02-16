from src.storage.db import get_session
from src.storage.models import Outreach
from sqlmodel import select

def check_outreach_status():
    with get_session() as session:
        statement = select(Outreach)
        results = session.exec(statement).all()
        print(f"Total Outreach records: {len(results)}")
        status_counts = {}
        for r in results:
            status_counts[r.status] = status_counts.get(r.status, 0) + 1
        
        for status, count in status_counts.items():
            print(f"Status '{status}': {count}")

if __name__ == "__main__":
    check_outreach_status()
