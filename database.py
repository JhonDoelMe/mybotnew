import sqlite3
import logging
from typing import List, Tuple, Optional

import config

logger = logging.getLogger(__name__)

DB_PATH = config.cfg.get('DB_PATH', 'bot.db')

def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER,
                region_id TEXT,
                PRIMARY KEY (user_id, region_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_currencies (
                user_id INTEGER,
                currency_code TEXT,
                PRIMARY KEY (user_id, currency_code)
            )
        """)
        conn.commit()
    logger.info("Database initialized successfully.")

def add_subscriber(user_id: int, region_id: Optional[str]) -> bool:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO subscriptions (user_id, region_id) VALUES (?, ?)", (user_id, region_id))
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Failed to add subscriber {user_id}: {e}")
        return False

def remove_subscriber(user_id: int, region_id: Optional[str] = None) -> bool:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            if region_id is None:
                cursor.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
            else:
                cursor.execute("DELETE FROM subscriptions WHERE user_id = ? AND region_id = ?", (user_id, region_id))
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Failed to remove subscriber {user_id}: {e}")
        return False

def is_subscribed(user_id: int, region_id: Optional[str] = None) -> bool:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            if region_id is None:
                cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE user_id = ?", (user_id,))
            else:
                cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE user_id = ? AND region_id = ?", (user_id, region_id))
            return cursor.fetchone()[0] > 0
    except sqlite3.Error as e:
        logger.error(f"Failed to check subscription for {user_id}: {e}")
        return False

def get_subscribers() -> List[Tuple[int, Optional[str]]]:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, region_id FROM subscriptions")
            return cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"Failed to get subscribers: {e}")
        return []

def add_user_currency(user_id: int, currency_code: str) -> bool:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO user_currencies (user_id, currency_code) VALUES (?, ?)", 
                         (user_id, currency_code))
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Failed to add currency {currency_code} for user {user_id}: {e}")
        return False

def get_user_currencies(user_id: int) -> Optional[List[str]]:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT currency_code FROM user_currencies WHERE user_id = ?", (user_id,))
            return [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Failed to get currencies for user {user_id}: {e}")
        return None