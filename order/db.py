
import os
import sqlite3
from pathlib import Path

DB_PATH = Path( os.getenv("ORDER_DB_PATH", "order/data/orders.db"))


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                book_title TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()

    print("[ORDER] Database initialized successfully.")


if __name__ == "__main__":
    init_db()
