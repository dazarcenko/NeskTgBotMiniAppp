import sqlite3
from pathlib import Path

DB_PATH = Path("shop.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            price REAL NOT NULL,
            image TEXT DEFAULT '',
            available INTEGER DEFAULT 1,
            FOREIGN KEY(category_id) REFERENCES categories(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            username TEXT,
            first_name TEXT,
            items TEXT,
            total REAL,
            delivery TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    count = conn.execute(
        "SELECT COUNT(*) FROM categories"
    ).fetchone()[0]

    if count == 0:
        conn.execute(
            "INSERT INTO categories (name) VALUES (?)",
            ("Категория 1",)
        )

        conn.execute(
            "INSERT INTO categories (name) VALUES (?)",
            ("Категория 2",)
        )

    conn.commit()
    conn.close()