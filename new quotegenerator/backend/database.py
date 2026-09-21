import sqlite3
from pathlib import Path
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_DIR = BASE_DIR / "database"
DATABASE_FILE = DATABASE_DIR / "quotes.db"


def get_connection():

    DATABASE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(DATABASE_FILE)

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():

    connection = get_connection()

    cursor = connection.cursor()

    try:

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote TEXT NOT NULL,
                author TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        connection.commit()

    finally:

        connection.close()


def save_quote(quote_text, author):

    connection = get_connection()

    cursor = connection.cursor()

    try:

        created_at = datetime.now().isoformat(
            timespec="seconds"
        )

        cursor.execute("""
            INSERT INTO quotes (
                quote,
                author,
                created_at
            )
            VALUES (?, ?, ?)
        """, (
            quote_text,
            author,
            created_at
        ))

        connection.commit()

        quote_id = cursor.lastrowid

        return {
            "id": quote_id,
            "quote": quote_text,
            "author": author,
            "created_at": created_at
        }

    finally:

        connection.close()


def get_all_quotes():

    connection = get_connection()

    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                quote,
                author,
                created_at
            FROM quotes
            ORDER BY id DESC
        """)

        rows = cursor.fetchall()

        quotes = []

        for row in rows:

            quotes.append({
                "id": row["id"],
                "quote": row["quote"],
                "author": row["author"],
                "created_at": row["created_at"]
            })

        return quotes

    finally:

        connection.close()