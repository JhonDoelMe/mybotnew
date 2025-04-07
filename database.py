import sqlite3
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)
DATABASE_NAME = 'bot_database.db'

@contextmanager
def get_connection():
    """Контекстный менеджер для работы с БД"""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def setup_database():
    """Инициализация таблиц БД"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                message_text TEXT UNIQUE NOT NULL,
                processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

if __name__ == '__main__':
    setup_database()
    print(f"База данных '{DATABASE_NAME}' успешно настроена.")