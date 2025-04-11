import sqlite3
import os
from typing import Dict, Optional, Union
from contextlib import contextmanager

DATABASE_PATH = "bot_database.db"

# Контекстный менеджер для работы с БД
@contextmanager
def get_connection():
    """Создать или получить соединение с базой данных"""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def init_db():
    """Инициализация базы данных"""
    with get_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                notify_air_alerts INTEGER DEFAULT 0,
                region_id TEXT,
                region_name TEXT,
                city TEXT,
                currency_preference TEXT DEFAULT 'USD',
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

def get_user_settings(conn, user_id: int) -> Dict[str, Optional[Union[int, str]]]:
    """Получить настройки пользователя"""
    cursor = conn.execute(
        "SELECT notify_air_alerts, region_id, region_name, city, currency_preference "
        "FROM user_settings WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    
    return {
        "notify_air_alerts": row["notify_air_alerts"] if row else 0,
        "region_id": row["region_id"] if row else None,
        "region_name": row["region_name"] if row else None,
        "city": row["city"] if row else None,
        "currency_preference": row["currency_preference"] if row else "USD"
    } if row else {
        "notify_air_alerts": 0,
        "region_id": None,
        "region_name": None,
        "city": None,
        "currency_preference": "USD"
    }

def update_user_setting(conn, user_id: int, key: str, value: Union[str, int]):
    """Обновить настройку пользователя"""
    allowed_keys = {
        'notify_air_alerts': 'INTEGER',
        'region_id': 'TEXT',
        'region_name': 'TEXT',
        'city': 'TEXT',
        'currency_preference': 'TEXT'
    }
    
    if key not in allowed_keys:
        raise ValueError(f"Invalid setting key: {key}")
    
    # Проверка типа значения
    if allowed_keys[key] == 'INTEGER' and not isinstance(value, int):
        raise ValueError(f"Value for {key} must be integer")
    elif allowed_keys[key] == 'TEXT' and not isinstance(value, str):
        raise ValueError(f"Value for {key} must be string")
    
    conn.execute(
        "INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)",
        (user_id,)
    )
    conn.execute(
        f"UPDATE user_settings SET {key} = ?, last_updated = CURRENT_TIMESTAMP WHERE user_id = ?",
        (value, user_id)
    )
    conn.commit()

if __name__ == "__main__":
    init_db()
    print("База данных инициализирована")