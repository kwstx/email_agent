import json
from src.storage.db import seed_signals, init_db
from main import load_config

def main():
    config = load_config()
    print("Seeding new signals...")
    seed_signals(config)
    print("Done.")

if __name__ == "__main__":
    main()
