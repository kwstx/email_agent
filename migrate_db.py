import sqlite3
import os
from loguru import logger

def migrate_db():
    db_path = "data/prospects.db"
    if not os.path.exists(db_path):
        logger.warning(f"Database {db_path} not found. init_db will create it with correct schema.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Add columns to company table
    try:
        cursor.execute("ALTER TABLE company ADD COLUMN agent_maturity_level TEXT")
        logger.info("Added agent_maturity_level to company table")
    except sqlite3.OperationalError:
        logger.info("agent_maturity_level already exists in company table")

    try:
        cursor.execute("ALTER TABLE company ADD COLUMN signal_metadata TEXT")
        logger.info("Added signal_metadata to company table")
    except sqlite3.OperationalError:
        logger.info("signal_metadata already exists in company table")

    # Add columns to companysignallink table
    try:
        cursor.execute("ALTER TABLE companysignallink ADD COLUMN intensity FLOAT DEFAULT 0.0")
        logger.info("Added intensity to companysignallink table")
    except sqlite3.OperationalError:
        logger.info("intensity already exists in companysignallink table")

    try:
        cursor.execute("ALTER TABLE companysignallink ADD COLUMN occurrences INTEGER DEFAULT 0")
        logger.info("Added occurrences to companysignallink table")
    except sqlite3.OperationalError:
        logger.info("occurrences already exists in companysignallink table")

    try:
        cursor.execute("ALTER TABLE contact ADD COLUMN relevance_score INTEGER DEFAULT 0")
        logger.info("Added relevance_score to contact table")
    except sqlite3.OperationalError:
        logger.info("relevance_score already exists in contact table")

    conn.commit()
    conn.close()
    logger.success("Database migration completed.")

if __name__ == "__main__":
    migrate_db()
