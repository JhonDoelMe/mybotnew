import sqlite3
import os

DATABASE_PATH = "bot_database.db"

def get_connection():
    """Создать или получить соединение с базой данных"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Возвращает результаты как словари
    return conn

def init_db(conn):
    """Инициализация базы данных"""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            notify_air_alerts INTEGER DEFAULT 0,
            region_id TEXT,
            region_name TEXT,
            city TEXT,              -- Для weather.py
            currency_preference TEXT -- Для currency.py
        )
    ''')
    conn.commit()

def get_user_settings(conn, user_id):
    """Получить настройки пользователя"""
    cursor = conn.execute(
        "SELECT notify_air_alerts, region_id, region_name, city, currency_preference "
        "FROM user_settings WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    if row:
        return {
            "notify_air_alerts": row["notify_air_alerts"],
            "region_id": row["region_id"],
            "region_name": row["region_name"],
            "city": row["city"],
            "currency_preference": row["currency_preference"]
        }
    # Значения по умолчанию
    return {
        "notify_air_alerts": 0,
        "region_id": None,
        "region_name": None,
        "city": None,
        "currency_preference": "USD"
    }

def update_user_setting(conn, user_id, key, value):
    """Обновить настройку пользователя"""
    # Сначала вставляем запись, если её нет, сохраняя существующие значения
    conn.execute(
        "INSERT OR IGNORE INTO user_settings (user_id, notify_air_alerts, region_id, region_name, city, currency_preference) "
        "VALUES (?, 0, NULL, NULL, NULL, 'USD')",
        (user_id,)
    )
    # Обновляем указанное поле
    conn.execute(
        f"UPDATE user_settings SET {key} = ? WHERE user_id = ?",
        (value, user_id)
    )
    conn.commit()

if __name__ == "__main__":
    # Инициализация базы при запуске файла напрямую (для тестирования)
    with get_connection() as conn:
        init_db(conn)
        print("База данных инициализирована")