from src.storage.db import get_session
from src.storage.models import Outreach
from sqlmodel import select

def reset_failed():
    with get_session() as session:
        statement = select(Outreach).where(Outreach.status == "failed")
        results = session.exec(statement).all()
        print(f"Resetting {len(results)} failed outreaches to 'draft'...")
        for r in results:
            r.status = "draft"
            session.add(r)
        session.commit()

if __name__ == "__main__":
    reset_failed()
