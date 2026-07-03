"""
JARVIS — Database Persistence Layer
Provides SQLite database connection management and schema persistence initializers.
"""

import os
import sqlite3
import logging
from backend.config import DATA_DIR

logger = logging.getLogger("core.database")
DB_PATH = os.path.join(DATA_DIR, "databases", "jarvis.db")

def get_db_connection() -> sqlite3.Connection:
    """Retrieve an active, autocommit-enabled, row-formatted connection to the SQLite database."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    # Enable isolation_level=None for autocommit mode (handled explicitly by transactions)
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """Initialize core relational schemas on startup."""
    logger.info(f"Initializing SQLite persistent database at: {DB_PATH}")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 1. Profile Configurations Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS profile_configs (
            user_id TEXT PRIMARY KEY,
            config TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # 2. Conversation History Perspersist Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            session_id TEXT PRIMARY KEY,
            user_id TEXT,
            title TEXT,
            messages TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.commit()
        logger.info("Database schemas verified/created successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize SQLite database: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()
