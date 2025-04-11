# database.py
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
    """Инициализирует базу данных и создает таблицу подписчиков, если она не существует."""
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscribers (
                    user_id INTEGER PRIMARY KEY,
                    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Проверка и добавление колонки subscribed_at для старых баз данных
            cursor.execute("PRAGMA table_info(subscribers)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'subscribed_at' not in columns:
                cursor.execute("ALTER TABLE subscribers ADD COLUMN subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                logger.info("Added 'subscribed_at' column to subscribers table.")
            conn.commit()
            logger.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
        raise  # Пробрасываем исключение дальше, чтобы приложение знало об ошибке

def add_subscriber(user_id: int) -> bool:
    """
    Добавляет пользователя в список подписчиков.
    Возвращает True при успехе, False при ошибке.
    """
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()
            # Используем INSERT OR IGNORE, чтобы не вызывать ошибку при попытке добавить существующего пользователя
            cursor.execute("INSERT OR IGNORE INTO subscribers (user_id, subscribed_at) VALUES (?, ?)",
                           (user_id, datetime.now()))
            conn.commit()
            # Проверяем, была ли строка действительно вставлена (или уже существовала)
            return cursor.rowcount > 0 or is_subscribed(user_id) # Вернет True, если вставили или уже был подписан
    except sqlite3.Error as e:
        logger.error(f"Database error in add_subscriber for user {user_id}: {e}")
        return False

def remove_subscriber(user_id: int) -> bool:
    """
    Удаляет пользователя из списка подписчиков.
    Возвращает True при успехе, False при ошибке.
    """
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM subscribers WHERE user_id = ?", (user_id,))
            conn.commit()
            # Возвращает True, если строка была удалена
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error in remove_subscriber for user {user_id}: {e}")
        return False

def is_subscribed(user_id: int) -> bool:
    """
    Проверяет, подписан ли пользователь.
    Возвращает True, если подписан, иначе False.
    """
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM subscribers WHERE user_id = ?", (user_id,))
            return cursor.fetchone() is not None
    except sqlite3.Error as e:
        logger.error(f"Database error in is_subscribed for user {user_id}: {e}")
        return False

def get_subscribers() -> List[int]:
    """
    Возвращает список ID всех подписчиков.
    """
    subscribers_list: List[int] = []
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM subscribers")
            # fetchall() возвращает список кортежей [(id1,), (id2,)]
            rows: List[Tuple[int]] = cursor.fetchall()
            subscribers_list = [row[0] for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Database error in get_subscribers: {e}")
        # Возвращаем пустой список в случае ошибки
    return subscribers_list