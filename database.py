import sqlite3
import os
from datetime import datetime

DB_PATH = 'plants.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_plants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plant_name TEXT NOT NULL,
            watering TEXT,
            lighting TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            photo_file_id TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")


def register_user(user_id, username=None, first_name=None, last_name=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name))

        conn.commit()
        return True
    except Exception as e:
        print(f"Ошибка при регистрации пользователя: {e}")
        return False
    finally:
        conn.close()


def add_plant_to_garden(user_id, plant_name, watering, lighting, photo_file_id=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO user_plants (user_id, plant_name, watering, lighting, photo_file_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, plant_name, watering, lighting, photo_file_id))

        conn.commit()
        return True
    except Exception as e:
        print(f"Ошибка при добавлении растения: {e}")
        return False
    finally:
        conn.close()


def get_user_plants(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT plant_name, watering, lighting, added_at, photo_file_id
            FROM user_plants 
            WHERE user_id = ? 
            ORDER BY added_at DESC
        ''', (user_id,))

        plants = cursor.fetchall()
        return plants
    except Exception as e:
        print(f"Ошибка при получении растений: {e}")
        return []
    finally:
        conn.close()


def get_plant_count(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT COUNT(*) FROM user_plants WHERE user_id = ?
        ''', (user_id,))

        count = cursor.fetchone()[0]
        return count
    except Exception as e:
        print(f"Ошибка при подсчёте растений: {e}")
        return 0
    finally:
        conn.close()


def delete_plant(user_id, plant_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT id FROM user_plants 
            WHERE user_id = ? AND plant_name = ? 
            LIMIT 1
        ''', (user_id, plant_name))

        result = cursor.fetchone()
        if result:
            plant_id = result[0]
            cursor.execute('''
                DELETE FROM user_plants 
                WHERE id = ?
            ''', (plant_id,))
            conn.commit()
            return True
        return False
    except Exception as e:
        print(f"Ошибка при удалении растения: {e}")
        return False
    finally:
        conn.close()


def clear_user_garden(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute('DELETE FROM user_plants WHERE user_id = ?', (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Ошибка при очистке сада: {e}")
        return False
    finally:
        conn.close()


def update_plant_photo(user_id, plant_name, photo_file_id):
    """Обновляет фото растения"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE user_plants 
            SET photo_file_id = ? 
            WHERE user_id = ? AND plant_name = ?
        ''', (photo_file_id, user_id, plant_name))

        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Ошибка при обновлении фото растения: {e}")
        return False
    finally:
        conn.close()


def get_plant_by_name(user_id, plant_name):
    """Получает информацию о конкретном растении по имени"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT plant_name, watering, lighting, added_at, photo_file_id
            FROM user_plants 
            WHERE user_id = ? AND plant_name = ?
        ''', (user_id, plant_name))

        plant = cursor.fetchone()
        return plant
    except Exception as e:
        print(f"Ошибка при получении растения: {e}")
        return None
    finally:
        conn.close()
