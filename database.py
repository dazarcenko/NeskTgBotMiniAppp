import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "shop.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, image TEXT DEFAULT '')""")
    conn.execute("""CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, category_id INTEGER NOT NULL, name TEXT NOT NULL, description TEXT DEFAULT '', price REAL NOT NULL, image TEXT DEFAULT '', available INTEGER DEFAULT 1, FOREIGN KEY(category_id) REFERENCES categories(id))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER, username TEXT, first_name TEXT, items TEXT, total REAL, delivery TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    cols = {row[1] for row in conn.execute("PRAGMA table_info(categories)").fetchall()}
    if "image" not in cols:
        conn.execute("ALTER TABLE categories ADD COLUMN image TEXT DEFAULT ''")
    count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    if count == 0:
        conn.execute("INSERT INTO categories (name, image) VALUES (?, ?)", ("Жижа", ""))
        conn.execute("INSERT INTO categories (name, image) VALUES (?, ?)", ("Подсистемы", ""))
    else:
        conn.execute("UPDATE categories SET name=? WHERE id=1", ("Жижа",))
        conn.execute("UPDATE categories SET name=? WHERE id=2", ("Подсистемы",))
    conn.commit()
    conn.close()
