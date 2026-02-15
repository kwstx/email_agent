
from sqlmodel import delete
from src.storage.db import get_session
from src.storage.models import Outreach

def reset_outreach():
    with get_session() as session:
        statement = delete(Outreach)
        session.exec(statement)
        session.commit()
    print("Outreach records cleared.")

if __name__ == "__main__":
    reset_outreach()
