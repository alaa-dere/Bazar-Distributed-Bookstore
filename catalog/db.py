
import os
import sqlite3
from pathlib import Path

DB_PATH = Path( os.getenv("CATALOG_DB_PATH", "catalog/data/catalog.db"))

INITIAL_BOOKS = [
    (1, "How to get a good grade in DOS in 40 minutes a day", "distributed systems", 50.0, 5),
    (2, "RPCs for Noobs",  "distributed systems", 50.0, 5),
    (3, "Xen and the Art of Surviving Undergraduate School", "undergraduate school", 40.0, 5),
    (4, "Cooking for the Impatient Undergrad","undergraduate school", 30.0, 5)
]


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                topic TEXT NOT NULL,
                price REAL NOT NULL CHECK(price >= 0),
                quantity INTEGER NOT NULL CHECK(quantity >= 0)
            )
        """)

        conn.executemany("""
            INSERT OR IGNORE INTO books
            (id, title, topic, price, quantity)
            VALUES (?, ?, ?, ?, ?)
        """, INITIAL_BOOKS)

        conn.commit()

    print("[CATALOG] Database initialized successfully.")


if __name__ == "__main__":
    init_db()
