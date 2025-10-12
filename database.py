import sqlite3
import datetime
from config import DB_FILE

# --- Helper Functions ---

def _dict_factory(cursor, row):
    """Converts database rows into dictionaries.

    This allows accessing columns by name instead of index.

    Args:
        cursor: The database cursor object.
        row: The row tuple from the database.

    Returns:
        A dictionary representation of the database row.
    """
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def _get_db_connection(dict_cursor=False):
    """Gets a connection to the SQLite database.

    Args:
        dict_cursor (bool): If True, the connection will use a row factory
                            that returns rows as dictionaries.

    Returns:
        An sqlite3.Connection object.
    """
    conn = sqlite3.connect(DB_FILE)
    if dict_cursor:
        conn.row_factory = _dict_factory
    return conn

# --- Initialization ---

def init_db():
    """
    Initializes the database, creating tables if they don't exist.

    Ensures that the 'logs' and 'relay_log' tables are created with the correct
    schema. It also handles schema migrations, such as adding the 'lux' column
    or removing obsolete columns. This function manages its own database connection.
    """
    conn = _get_db_connection()
    c = conn.cursor()
    # Create table for sensor logs
    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            dht22_air_temp REAL,
            dht22_humidity REAL,
            ds18b20_soil_temp REAL,
            soil_raw REAL,
            soil_voltage REAL,
            soil_percent REAL,
            lux REAL
        )
    """)
    # Create table for relay events
    c.execute("""
        CREATE TABLE IF NOT EXISTS relay_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            relay_name TEXT,
            action TEXT,
            source TEXT
        )
    """)

    # --- Schema Migration (if necessary) ---
    c.execute("PRAGMA table_info(logs)")
    # fetch column names (they are at index 1)
    cols = [row[1] for row in c.fetchall()]

    if "lux" not in cols:
        print("[DB] Adding 'lux' column to 'logs' table...")
        c.execute("ALTER TABLE logs ADD COLUMN lux REAL")

    if "stable" in cols:
        print("[DB] Removing old 'stable' column from 'logs' table...")
        # The safest way to remove a column in SQLite
        c.execute("CREATE TABLE logs_new AS SELECT id, timestamp, dht22_air_temp, dht22_humidity, ds18b20_soil_temp, soil_raw, soil_voltage, soil_percent, lux FROM logs")
        c.execute("DROP TABLE logs")
        c.execute("ALTER TABLE logs_new RENAME TO logs")
        print("[DB] 'stable' column successfully removed.")

    conn.commit()
    conn.close()

# --- Sensor Log Functions ---

def insert_log(timestamp, air_temp, air_humidity, soil_temp, soil_raw, soil_voltage, soil_percent, lux):
    """Inserts a single row of sensor data into the database.

    This function manages its own database connection.

    Args:
        timestamp (str): The timestamp of the reading (YYYY-MM-DD HH:MM:SS).
        air_temp (float): Air temperature from DHT22 sensor.
        air_humidity (float): Air humidity from DHT22 sensor.
        soil_temp (float): Soil temperature from DS18B20 sensor.
        soil_raw (float): Raw ADC value from the soil moisture sensor.
        soil_voltage (float): Voltage reading from the soil moisture sensor.
        soil_percent (float): Calculated soil moisture in percent.
        lux (float): Light level in lux from BH1750 sensor.
    """
    sql = """
        INSERT INTO logs (timestamp, dht22_air_temp, dht22_humidity, ds18b20_soil_temp,
                          soil_raw, soil_voltage, soil_percent, lux)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    conn = _get_db_connection()
    try:
        conn.execute(sql, (timestamp, air_temp, air_humidity, soil_temp, soil_raw, soil_voltage, soil_percent, lux))
        conn.commit()
    except sqlite3.Error as e:
        print(f"[DB ERROR] Failed to insert log: {e}")
    finally:
        conn.close()

def get_logs(limit=100, order="ASC"):
    """Fetches sensor logs from the database, sorted by ID.

    Args:
        limit (int): The maximum number of logs to retrieve.
        order (str): The sort order, either "ASC" for ascending or "DESC" for descending.

    Returns:
        A list of dictionaries, where each dictionary represents a log entry.
    """
    conn = _get_db_connection(dict_cursor=True)
    c = conn.cursor()
    order_clause = "DESC" if order.upper() == "DESC" else "ASC"
    c.execute(f"SELECT * FROM logs ORDER BY id {order_clause} LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_logs_where(where_clause, params=[]):
    """Fetches logs that satisfy a dynamic but safe WHERE condition.

    Args:
        where_clause (str): A string containing the WHERE conditions (e.g., "lux > ? AND soil_percent < ?").
        params (list): A list of parameters to be safely substituted into the where_clause.

    Returns:
        A list of dictionaries representing the log entries that match the query,
        or an empty list if an error occurs.
    """
    conn = _get_db_connection(dict_cursor=True)
    c = conn.cursor()
    query = "SELECT * FROM logs"
    if where_clause:
        query += f" WHERE {where_clause}"
    query += " ORDER BY id ASC"

    try:
        c.execute(query, params)
        rows = c.fetchall()
    except sqlite3.Error as e:
        print(f"[DB ERROR] Query failed: {e}")
        rows = []
    finally:
        conn.close()
    return rows

def delete_logs_by_id(ids):
    """Deletes logs based on a list or string of IDs.

    Args:
        ids (list|str): A list of integer IDs or a comma-separated string of IDs to delete.

    Returns:
        A tuple (bool, str) indicating success or failure and a corresponding message.
    """
    if not ids:
        return False, "No IDs provided for deletion."

    try:
        if isinstance(ids, str):
            id_list = [int(x.strip()) for x in ids.split(',') if x.strip().isdigit()]
        elif isinstance(ids, list):
            id_list = [int(x) for x in ids]
        else:
            return False, "Invalid ID format."
    except ValueError:
        return False, "IDs must be numbers."

    if not id_list:
        return False, "No valid IDs to delete."

    conn = _get_db_connection()
    c = conn.cursor()
    placeholders = ",".join("?" for _ in id_list)
    c.execute(f"DELETE FROM logs WHERE id IN ({placeholders})", id_list)
    deleted_count = c.rowcount
    conn.commit()
    conn.close()
    return True, f"Deleted {deleted_count} records."

# --- Relay Log Functions ---

def insert_relay_event(relay_name, action, source="unknown"):
    """Records a relay ON/OFF event in the database.

    Args:
        relay_name (str): The name of the relay (e.g., "RELAY1").
        action (str): The action taken ("ON" or "OFF").
        source (str): The source of the event (e.g., "web", "auto", "manual").
    """
    conn = _get_db_connection()
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = "INSERT INTO relay_log (timestamp, relay_name, action, source) VALUES (?, ?, ?, ?)"
    conn.execute(sql, (ts, relay_name, action, source))
    conn.commit()
    conn.close()

def get_relay_log(limit=10):
    """Fetches the last N relay events.

    Args:
        limit (int): The maximum number of relay events to retrieve.

    Returns:
        A list of dictionaries, where each dictionary represents a relay event.
    """
    conn = _get_db_connection(dict_cursor=True)
    c = conn.cursor()
    c.execute("SELECT * FROM relay_log ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

# --- Administration Functions (for manage.py) ---

def get_sql_data():
    """Prints all rows from the 'logs' table to the console.

    This is intended for use with the command-line interface in manage.py.
    """
    conn = _get_db_connection(dict_cursor=True)
    rows = conn.execute("SELECT * FROM logs ORDER BY id").fetchall()
    conn.close()
    for row in rows:
        print(dict(row))

def delete_sql_data(ids=None, delete_all=False):
    """Deletes data from the 'logs' table (intended for CLI use).

    Args:
        ids (str, optional): A comma-separated string of IDs or ranges (e.g., "1,3,5-8").
                             Defaults to None.
        delete_all (bool, optional): If True, all records from the 'logs' table
                                     will be deleted. Defaults to False.
    """
    conn = _get_db_connection()
    c = conn.cursor()

    if delete_all:
        c.execute("DELETE FROM logs")
        c.execute("DELETE FROM sqlite_sequence WHERE name='logs'") # Reset autoincrement
        print("All records from the 'logs' table have been deleted.")
    elif ids:
        try:
            id_list = []
            for part in ids.split(','):
                part = part.strip()
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    id_list.extend(range(start, end + 1))
                else:
                    id_list.append(int(part))

            placeholders = ",".join("?" for _ in id_list)
            c.execute(f"DELETE FROM logs WHERE id IN ({placeholders})", id_list)
            print(f"Deleted records with IDs: {id_list}")
        except ValueError:
            print("Error: IDs must be numbers (e.g., 1,3,5-8).")
    else:
        print("Nothing specified to delete. Use --ids or --all.")

    conn.commit()
    conn.close()