import sqlite3
import os
from loguru import logger

def migrate_db():
    db_path = "data/prospects.db"
    
    # Ensure directory exists
    os.makedirs("data", exist_ok=True)
    
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

    # NEW COLUMNS FOR OUTREACH SEQUENCING
    try:
        cursor.execute("ALTER TABLE contact ADD COLUMN outreach_stage INTEGER DEFAULT 0")
        logger.info("Added outreach_stage to contact table")
    except sqlite3.OperationalError:
        logger.info("outreach_stage already exists in contact table")

    try:
        cursor.execute("ALTER TABLE contact ADD COLUMN last_outreach_sent_at TIMESTAMP")
        logger.info("Added last_outreach_sent_at to contact table")
    except sqlite3.OperationalError:
        logger.info("last_outreach_sent_at already exists in contact table")
        
    try:
        cursor.execute("ALTER TABLE outreach ADD COLUMN stage INTEGER DEFAULT 1")
        logger.info("Added stage to outreach table")
    except sqlite3.OperationalError:
        logger.info("stage already exists in outreach table")

    try:
        cursor.execute("ALTER TABLE company ADD COLUMN employee_count INTEGER")
        logger.info("Added employee_count to company table")
    except sqlite3.OperationalError:
        logger.info("employee_count already exists in company table")

    conn.commit()

    # Create suppressionlist table if it doesn't exist
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suppressionlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                value TEXT NOT NULL UNIQUE,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_suppressionlist_value ON suppressionlist (value)")
        logger.info("Ensured suppressionlist table exists")
    except sqlite3.OperationalError as e:
        logger.info(f"suppressionlist table: {e}")

    # Create reply table if it doesn't exist
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reply (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL REFERENCES contact(id),
                content TEXT NOT NULL,
                classification TEXT NOT NULL,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                original_subject TEXT,
                thread_id TEXT
            )
        """)
        logger.info("Ensured reply table exists")
    except sqlite3.OperationalError as e:
        logger.info(f"reply table: {e}")

    conn.commit()
    conn.close()
    logger.success("Database migration completed.")

if __name__ == "__main__":
    migrate_db()
