# database.py
import sqlite3
from contextlib import contextmanager
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
DATABASE_NAME = 'bot_database.db'

@contextmanager
def get_connection():
    """Контекстный менеджер для подключения к БД"""
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
    """Инициализация структуры БД"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language_code TEXT,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                city TEXT DEFAULT 'Kyiv',
                currency_preference TEXT DEFAULT 'USD',
                notify_air_alerts BOOLEAN DEFAULT 1,
                oblast_uid TEXT,  -- Добавлено для области
                location_uid TEXT,  -- Добавлено для конкретной локации
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
            
            CREATE TABLE IF NOT EXISTS processed_news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                channel_id TEXT NOT NULL,
                message_text TEXT NOT NULL,
                processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                UNIQUE(user_id, message_text)
            );
            
            CREATE INDEX IF NOT EXISTS idx_processed_news_user_message 
            ON processed_news (user_id, message_text);
        """)
        conn.commit()

def get_or_create_user(conn, user_data: dict):
    """Регистрация/получение пользователя"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO users 
        (user_id, username, first_name, last_name, language_code) 
        VALUES (?, ?, ?, ?, ?)
    """, (
        user_data['id'],
        user_data.get('username'),
        user_data.get('first_name'),
        user_data.get('last_name'),
        user_data.get('language_code')
    ))
    conn.commit()

def get_user_settings(conn, user_id: int):
    """Получение настроек пользователя"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT city, currency_preference, notify_air_alerts, oblast_uid, location_uid
        FROM user_settings 
        WHERE user_id = ?
    """, (user_id,))
    result = cursor.fetchone()
    return dict(result) if result else {
        'city': 'Kyiv',
        'currency_preference': 'USD',
        'notify_air_alerts': True,
        'oblast_uid': None,
        'location_uid': None
    }

def update_user_setting(conn, user_id: int, setting: str, value):
    """Обновление настроек пользователя"""
    cursor = conn.cursor()
    cursor.execute(f"""
        UPDATE user_settings 
        SET {setting} = ? 
        WHERE user_id = ?
    """, (value, user_id))
    if cursor.rowcount == 0:  # Если записи нет, создаем новую
        cursor.execute(f"""
            INSERT INTO user_settings (user_id, {setting})
            VALUES (?, ?)
        """, (user_id, value))
    conn.commit()
    
def log_news_processed(conn, user_id: int, channel_id: str, message_text: str):
    """Логирование обработанных новостей"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO processed_news 
        (user_id, channel_id, message_text) 
        VALUES (?, ?, ?)
    """, (user_id, channel_id, message_text))
    conn.commit()

def is_news_processed(conn, user_id: int, message_text: str):
    """Проверка новости на обработку"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM processed_news 
        WHERE user_id = ? AND message_text = ?
    """, (user_id, message_text))
    return cursor.fetchone() is not None

if __name__ == '__main__':
    setup_database()