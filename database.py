import sqlite3
import datetime
from config import DB_FILE

# --- Pomoćne funkcije ---

def _dict_factory(cursor, row):
    """Pretvara retke iz baze u rječnike (dict)."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def _get_db_connection(dict_cursor=False):
    """Vraća konekciju na bazu. Opcionalno koristi dict_factory."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    if dict_cursor:
        conn.row_factory = _dict_factory
    return conn

# --- Inicijalizacija ---

def init_db():
    """
    Osigurava da baza i sve tablice postoje i imaju ispravnu shemu.
    """
    conn = _get_db_connection()
    c = conn.cursor()
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
            lux REAL,
            stable INTEGER DEFAULT 1
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS relay_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            relay_name TEXT,
            action TEXT,
            source TEXT
        )
    """)

    c.execute("PRAGMA table_info(logs)")
    cols = [row[1] for row in c.fetchall()]
    if "lux" not in cols:
        c.execute("ALTER TABLE logs ADD COLUMN lux REAL")
    if "stable" not in cols:
        c.execute("ALTER TABLE logs ADD COLUMN stable INTEGER DEFAULT 1")

    conn.commit()
    conn.close()

# --- Funkcije za rad s logovima senzora ---

def insert_log(timestamp, air_temp, air_humidity, soil_temp, soil_raw, soil_voltage, soil_percent, lux, stable):
    """Upisuje jedan red podataka od senzora u bazu."""
    sql = """
        INSERT INTO logs (timestamp, dht22_air_temp, dht22_humidity, ds18b20_soil_temp,
                          soil_raw, soil_voltage, soil_percent, lux, stable)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    conn = _get_db_connection()
    try:
        conn.execute(sql, (timestamp, air_temp, air_humidity, soil_temp, soil_raw, soil_voltage, soil_percent, lux, stable))
        conn.commit()
    except sqlite3.Error as e:
        print(f"[DB ERROR] Neuspješan upis u log: {e}")
    finally:
        conn.close()

def get_logs(limit=100, order="ASC"):
    conn = _get_db_connection(dict_cursor=True)
    c = conn.cursor()
    order_clause = "DESC" if order.upper() == "DESC" else "ASC"
    c.execute(f"SELECT * FROM logs ORDER BY id {order_clause} LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_logs_where(where_clause, params=[]):
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
        print(f"[DB ERROR] Greška u upitu: {e}")
        rows = []
    finally:
        conn.close()
    return rows

def delete_logs_by_id(ids):
    """Briše logove na temelju liste ID-eva. Podržava ['all'] za brisanje svih zapisa."""
    if not ids or not isinstance(ids, list):
        return False, "Neispravan format zahtjeva."

    conn = _get_db_connection()
    c = conn.cursor()
    deleted_count_str = "0"

    try:
        # Slučaj kada frontend pošalje ['all']
        if ids[0] == 'all':
            c.execute("DELETE FROM logs")
            # Resetiraj autoincrement brojač
            c.execute("DELETE FROM sqlite_sequence WHERE name='logs'")
            # Iako c.rowcount ne radi za DELETE bez WHERE, znamo da su svi obrisani
            deleted_count_str = "svi"
        else:
            # Slučaj kada frontend pošalje listu brojeva [1, 2, 3]
            id_list = [int(i) for i in ids]
            if not id_list:
                return False, "Nema valjanih ID-eva za brisanje."

            placeholders = ",".join("?" for _ in id_list)
            c.execute(f"DELETE FROM logs WHERE id IN ({placeholders})", id_list)
            deleted_count_str = str(c.rowcount)

        conn.commit()
        return True, f"Obrisano {deleted_count_str} zapisa."
    except (ValueError, TypeError):
        conn.rollback()
        return False, "ID-evi moraju biti brojevi."
    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Greška u bazi: {e}"
    finally:
        conn.close()

# --- Funkcije za rad s logovima releja ---

def insert_relay_event(relay_name, action, source="unknown"):
    conn = None
    try:
        conn = _get_db_connection()
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sql = "INSERT INTO relay_log (timestamp, relay_name, action, source) VALUES (?, ?, ?, ?)"
        conn.execute(sql, (ts, relay_name, action, source))
        conn.commit()
        print(f"[DB] Uspješno zabilježen događaj za {relay_name}: {action}")
    except sqlite3.Error as e:
        print(f"[DB ERROR] Neuspješan upis događaja za relej: {e}")
    finally:
        if conn:
            conn.close()

def get_relay_log(limit=15):
    conn = _get_db_connection(dict_cursor=True)
    c = conn.cursor()
    c.execute("SELECT * FROM relay_log ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

# --- Funkcije za administraciju (za manage.py) ---

def get_sql_data():
    conn = _get_db_connection(dict_cursor=True)
    rows = conn.execute("SELECT * FROM logs ORDER BY id").fetchall()
    conn.close()
    for row in rows:
        print(dict(row))

def delete_sql_data(ids=None, delete_all=False):
    conn = _get_db_connection()
    c = conn.cursor()

    if delete_all:
        c.execute("DELETE FROM logs")
        c.execute("DELETE FROM sqlite_sequence WHERE name='logs'")
        print("Svi zapisi iz tablice 'logs' su obrisani.")
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
            print(f"Obrisani zapisi s ID-evima: {id_list}")
        except ValueError:
            print("Greška: ID-evi moraju biti brojevi (npr. 1,3,5-8).")
    else:
        print("Nije specificirano što treba obrisati. Koristi --ids ili --all.")

    conn.commit()
    conn.close()