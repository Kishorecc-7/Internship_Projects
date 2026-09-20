import sqlite3
from pathlib import Path


# ---------------------------------------
# Database location
# ---------------------------------------

# Find the project's main directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Store the database inside the database folder
DATABASE_DIR = BASE_DIR / "database"

DATABASE_FILE = DATABASE_DIR / "coffee.db"


# ---------------------------------------
# Default coffee categories
# ---------------------------------------

DEFAULT_COFFEES = [
    "Espresso",
    "Cappuccino",
    "Latte",
    "Americano",
    "Mocha"
]


# ---------------------------------------
# Get database connection
# ---------------------------------------

def get_connection():
    """
    Create and return a connection to SQLite.
    """

    # Make sure the database directory exists
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_FILE)

    # Return rows that can be accessed using column names
    connection.row_factory = sqlite3.Row

    return connection


# ---------------------------------------
# Initialize database
# ---------------------------------------

def initialize_database():
    """
    Create the coffees table if it does not exist.

    Insert default coffees only when the table is empty.
    """

    connection = get_connection()

    cursor = connection.cursor()


    # Create table if it does not already exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coffees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            votes INTEGER NOT NULL DEFAULT 0
        )
    """)


    # Check whether the table already contains coffees
    cursor.execute("SELECT COUNT(*) FROM coffees")

    coffee_count = cursor.fetchone()[0]


    # Insert default coffees only if the table is empty
    if coffee_count == 0:

        for coffee_name in DEFAULT_COFFEES:

            cursor.execute(
                """
                INSERT INTO coffees (name, votes)
                VALUES (?, ?)
                """,
                (coffee_name, 0)
            )


    # Save changes
    connection.commit()

    # Close the database connection
    connection.close()


# ---------------------------------------
# Get all coffees
# ---------------------------------------

def get_all_coffees():
    """
    Return all coffees from the database.
    """

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute("""
        SELECT id, name, votes
        FROM coffees
        ORDER BY id
    """)


    rows = cursor.fetchall()

    connection.close()


    # Convert SQLite rows into normal dictionaries
    coffees = []

    for row in rows:

        coffee = {
            "id": row["id"],
            "name": row["name"],
            "votes": row["votes"]
        }

        coffees.append(coffee)


    return coffees


# ---------------------------------------
# Get one coffee by ID
# ---------------------------------------

def get_coffee_by_id(coffee_id):
    """
    Find a coffee using its ID.

    Returns None if the coffee does not exist.
    """

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute("""
        SELECT id, name, votes
        FROM coffees
        WHERE id = ?
    """, (coffee_id,))


    row = cursor.fetchone()

    connection.close()


    if row is None:
        return None


    return {
        "id": row["id"],
        "name": row["name"],
        "votes": row["votes"]
    }


# ---------------------------------------
# Increase coffee vote
# ---------------------------------------

def increment_coffee_vote(coffee_id):
    """
    Increase the selected coffee's vote count by 1.

    Returns the updated coffee.
    """

    connection = get_connection()

    cursor = connection.cursor()


    # Increase votes by exactly 1
    cursor.execute("""
        UPDATE coffees
        SET votes = votes + 1
        WHERE id = ?
    """, (coffee_id,))


    # Save the change
    connection.commit()


    # Get the updated coffee
    cursor.execute("""
        SELECT id, name, votes
        FROM coffees
        WHERE id = ?
    """, (coffee_id,))


    row = cursor.fetchone()

    connection.close()


    return {
        "id": row["id"],
        "name": row["name"],
        "votes": row["votes"]
    }