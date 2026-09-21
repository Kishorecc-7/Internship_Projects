import sqlite3
from pathlib import Path


# Find the main project folder
BASE_DIR = Path(__file__).resolve().parent.parent

# Database folder
DATABASE_DIR = BASE_DIR / "database"

# SQLite database file
DATABASE_FILE = DATABASE_DIR / "team.db"


# Create a database connection
def get_connection():

    # Create the database folder if it doesn't exist
    DATABASE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(DATABASE_FILE)

    # Allows us to access columns by name
    connection.row_factory = sqlite3.Row

    return connection


# Create the users table
def initialize_database():

    connection = get_connection()

    cursor = connection.cursor()

    try:

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                available INTEGER NOT NULL DEFAULT 1
            )
        """)

        connection.commit()

        insert_sample_users(connection)

    finally:

        connection.close()


# Insert sample users if the table is empty
def insert_sample_users(connection):

    cursor = connection.cursor()

    # Check whether users already exist
    cursor.execute("SELECT COUNT(*) FROM users")

    user_count = cursor.fetchone()[0]

    # Don't insert anything if users already exist
    if user_count > 0:
        return

    sample_users = [
        ("John Smith", "Engineering", 1),
        ("Priya Kumar", "Design", 0),
        ("Alex Martin", "Marketing", 1),
        ("Sarah Wilson", "Human Resources", 1)
    ]

    cursor.executemany("""
        INSERT INTO users (
            name,
            department,
            available
        )
        VALUES (?, ?, ?)
    """, sample_users)

    connection.commit()


# Get all users
def get_all_users():

    connection = get_connection()

    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                name,
                department,
                available
            FROM users
            ORDER BY id
        """)

        rows = cursor.fetchall()

        users = []

        for row in rows:

            users.append({
                "id": row["id"],
                "name": row["name"],
                "department": row["department"],
                "available": bool(row["available"])
            })

        return users

    finally:

        connection.close()


# Update a user's availability
def update_user_availability(user_id, available):

    connection = get_connection()

    cursor = connection.cursor()

    try:

        # Check whether the user exists
        cursor.execute("""
            SELECT
                id,
                name,
                department,
                available
            FROM users
            WHERE id = ?
        """, (user_id,))

        row = cursor.fetchone()

        if row is None:
            return None

        # Convert Boolean to SQLite integer
        available_value = 1 if available else 0

        # Update availability
        cursor.execute("""
            UPDATE users
            SET available = ?
            WHERE id = ?
        """, (
            available_value,
            user_id
        ))

        connection.commit()

        # Get the updated user
        cursor.execute("""
            SELECT
                id,
                name,
                department,
                available
            FROM users
            WHERE id = ?
        """, (user_id,))

        updated_row = cursor.fetchone()

        return {
            "id": updated_row["id"],
            "name": updated_row["name"],
            "department": updated_row["department"],
            "available": bool(updated_row["available"])
        }

    finally:

        connection.close()