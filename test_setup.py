from src.storage.db import init_db, seed_signals, get_session
from src.storage.models import Signal
from sqlmodel import select
import json

def test_setup():
    print("Testing environment setup...")
    
    # Initialize DB
    init_db()
    
    # Load config and seed
    with open("scoring_config.json", "r") as f:
        config = json.load(f)
    seed_signals(config)
    
    # Verify signals
    with get_session() as session:
        signals = session.exec(select(Signal)).all()
        print(f"Successfully seeded {len(signals)} signals.")
        for s in signals[:3]:
            print(f" - {s.name} ({s.category}): {s.points}pts")

if __name__ == "__main__":
    test_setup()
