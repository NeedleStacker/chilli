import sqlite3
import datetime
from typing import List, Optional, Union

from config import DATABASE_FILE

def initialize_database() -> sqlite3.Connection:
    """
    Initializes the database and the 'logs' table if it doesn't exist.
    Also adds 'lux' and 'stable' columns if they are missing.

    Returns:
        sqlite3.Connection: The database connection object.
    """
    connection = sqlite3.connect(DATABASE_FILE)
    cursor = connection.cursor()

    # Create the 'logs' table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            dht22_air_temp REAL,
            dht22_humidity REAL,
            ds18b20_soil_temp REAL,
            soil_raw REAL,
            soil_voltage REAL,
            soil_percent REAL,
            lux REAL,
            stable INTEGER DEFAULT 1
        )
    """)
    connection.commit()

    # Check for and add missing columns for backward compatibility
    cursor.execute("PRAGMA table_info(logs)")
    columns = [row[1] for row in cursor.fetchall()]
    if "lux" not in columns:
        print("[DB] Adding 'lux' column to the logs table...")
        cursor.execute("ALTER TABLE logs ADD COLUMN lux REAL")
        connection.commit()
    if "stable" not in columns:
        print("[DB] Adding 'stable' column to the logs table...")
        cursor.execute("ALTER TABLE logs ADD COLUMN stable INTEGER DEFAULT 1;")
        connection.commit()

    return connection

def delete_logs(ids: Optional[str] = None, delete_all: bool = False) -> None:
    """
    Deletes log records from the database.

    Args:
        ids (Optional[str]): A comma-separated string of IDs or ID ranges (e.g., "1,3,5-10").
        delete_all (bool): If True, deletes all records. This requires a confirmation prompt.
    """
    connection = sqlite3.connect(DATABASE_FILE)
    cursor = connection.cursor()

    if delete_all:
        confirm = input("⚠️  Are you sure you want to delete ALL data from the database? (yes/no): ")
        if confirm.lower() == "yes":
            cursor.execute("DELETE FROM logs")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='logs'")  # Reset autoincrement
            connection.commit()
            print("✅ All records have been deleted and the index has been reset.")
        else:
            print("❌ Canceled deleting all records.")
    elif ids:
        try:
            id_list: List[int] = []
            for part in ids.split(","):
                part = part.strip()
                if "-" in part:
                    start, end = map(int, part.split("-"))
                    id_list.extend(range(start, end + 1))
                else:
                    id_list.append(int(part))

            id_list = sorted(list(set(id_list)))
            placeholders = ",".join("?" for _ in id_list)
            cursor.execute(f"DELETE FROM logs WHERE id IN ({placeholders})", id_list)
            connection.commit()
            print(f"✅ Deleted records with IDs: {id_list}")
        except ValueError:
            print("❌ Error: IDs must be numbers, e.g., 1,3,5 or 3-10.")
    else:
        print("⚠️ No IDs specified for deletion. Use --ids or --all.")

    connection.close()

def get_all_logs() -> List[sqlite3.Row]:
    """
    Retrieves and prints all logs from the database.

    Returns:
        List[sqlite3.Row]: A list of all log records.
    """
    connection = sqlite3.connect(DATABASE_FILE)
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM logs")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
    connection.close()
    return rows

# --- Relay Log Functions ---

def ensure_relay_log_table_exists() -> None:
    """Ensures the 'relay_log' table exists in the database."""
    connection = sqlite3.connect(DATABASE_FILE)
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relay_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            relay_name TEXT,
            action TEXT,
            source TEXT
        )
    """)
    connection.commit()
    connection.close()

def insert_relay_log_event(relay_name: str, action: str, source: str = "button") -> None:
    """
    Inserts a relay ON/OFF event into the 'relay_log' table.

    Args:
        relay_name (str): The name of the relay (e.g., "RELAY1").
        action (str): The action performed ("ON" or "OFF").
        source (str, optional): The source of the event. Defaults to "button".
    """
    ensure_relay_log_table_exists()
    connection = sqlite3.connect(DATABASE_FILE)
    cursor = connection.cursor()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO relay_log (timestamp, relay_name, action, source) VALUES (?, ?, ?, ?)",
        (timestamp, relay_name, action, source),
    )
    connection.commit()
    connection.close()
