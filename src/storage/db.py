import os
from sqlmodel import SQLModel, create_engine, Session, select
from loguru import logger
from .models import Signal

DB_FILE = "data/prospects.db"
engine = create_engine(f"sqlite:///{DB_FILE}", echo=False)

def init_db():
    """Initialize the database and create tables."""
    logger.info("Initializing database...")
    SQLModel.metadata.create_all(engine)
    logger.success("Database initialized.")

def get_session():
    """Get a new database session."""
    return Session(engine)

def seed_signals(scoring_config: dict):
    """Seed signals from the scoring configuration."""
    with get_session() as session:
        for category, signals in scoring_config.get("signals", {}).items():
            for signal_key, details in signals.items():
                existing = session.exec(select(Signal).where(Signal.name == signal_key)).first()
                if not existing:
                    signal = Signal(
                        name=signal_key,
                        description=details.get("description"),
                        category=category,
                        points=details.get("points", 0)
                    )
                    session.add(signal)
        session.commit()
    logger.info("Signals seeded from config.")
