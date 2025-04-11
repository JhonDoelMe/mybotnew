import sqlite3
import logging
from typing import List, Tuple, Optional
from datetime import datetime

DATABASE_FILE = 'bot_database.db'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def init_db() -> None:
    """
    Initializes the database and creates the subscribers table with region_id support.
    """
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscribers (
                    user_id INTEGER,
                    region_id TEXT,
                    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, region_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_region_id ON subscribers(region_id)")
            conn.commit()
            logger.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
        raise

def add_subscriber(user_id: int, region_id: Optional[str] = None) -> bool:
    """
    Adds a user to the subscribers list for a specific region or all regions.

    Args:
        user_id: Telegram user ID.
        region_id: Region ID from UkraineAlarm API, or None for all regions.

    Returns:
        bool: True if added or already subscribed, False on error.
    """
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO subscribers (user_id, region_id, subscribed_at) VALUES (?, ?, ?)",
                (user_id, region_id, datetime.now())
            )
            conn.commit()
            return cursor.rowcount > 0 or is_subscribed(user_id, region_id)
    except sqlite3.Error as e:
        logger.error(f"Database error in add_subscriber for user {user_id}, region {region_id}: {e}")
        return False

def remove_subscriber(user_id: int, region_id: Optional[str] = None) -> bool:
    """
    Removes a user from subscribers for a specific region or all regions.

    Args:
        user_id: Telegram user ID.
        region_id: Region ID, or None to remove all subscriptions.

    Returns:
        bool: True if removed, False on error or if not subscribed.
    """
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()
            if region_id:
                cursor.execute("DELETE FROM subscribers WHERE user_id = ? AND region_id = ?", (user_id, region_id))
            else:
                cursor.execute("DELETE FROM subscribers WHERE user_id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error in remove_subscriber for user {user_id}, region {region_id}: {e}")
        return False

def is_subscribed(user_id: int, region_id: Optional[str] = None) -> bool:
    """
    Checks if a user is subscribed to a specific region or any region.

    Args:
        user_id: Telegram user ID.
        region_id: Region ID, or None to check any subscription.

    Returns:
        bool: True if subscribed, False otherwise.
    """
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()
            if region_id:
                cursor.execute(
                    "SELECT 1 FROM subscribers WHERE user_id = ? AND region_id = ?",
                    (user_id, region_id)
                )
            else:
                cursor.execute("SELECT 1 FROM subscribers WHERE user_id = ?", (user_id,))
            return cursor.fetchone() is not None
    except sqlite3.Error as e:
        logger.error(f"Database error in is_subscribed for user {user_id}, region {region_id}: {e}")
        return False

def get_subscribers(region_id: Optional[str] = None) -> List[Tuple[int, Optional[str]]]:
    """
    Returns a list of subscribers, optionally filtered by region.

    Args:
        region_id: Region ID to filter by, or None for all subscribers.

    Returns:
        List[Tuple[int, Optional[str]]]: List of (user_id, region_id) tuples.
    """
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()
            if region_id:
                cursor.execute("SELECT user_id, region_id FROM subscribers WHERE region_id = ?", (region_id,))
            else:
                cursor.execute("SELECT user_id, region_id FROM subscribers")
            return cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"Database error in get_subscribers for region {region_id}: {e}")
        return []