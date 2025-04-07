# database.py
import sqlite3

DATABASE_NAME = 'bot_database.db'

def get_connection():
    """Возвращает подключение к базе данных."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # Для доступа к столбцам по имени
    return conn

def close_connection(conn):
    """Закрывает подключение к базе данных."""
    if conn:
        conn.close()

def setup_database():
    """Создает необходимые таблицы, если они не существуют."""
    conn = get_connection()
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
    close_connection(conn)

if __name__ == '__main__':
    setup_database()
    print(f"База данных '{DATABASE_NAME}' успешно настроена.")