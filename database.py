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
    conn = sqlite3.connect(DB_FILE)
    if dict_cursor:
        conn.row_factory = _dict_factory
    return conn

# --- Inicijalizacija ---

def init_db():
    """
    Osigurava da baza i sve tablice postoje i imaju ispravnu shemu.
    Sama upravlja svojom konekcijom.
    """
    conn = _get_db_connection()
    c = conn.cursor()
    # Kreiraj tablicu za logove senzora
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
    # Kreiraj tablicu za događaje releja
    c.execute("""
        CREATE TABLE IF NOT EXISTS relay_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            relay_name TEXT,
            action TEXT,
            source TEXT
        )
    """)

    # --- Migracija sheme (ako je potrebno) ---
    c.execute("PRAGMA table_info(logs)")
    # dohvati imena stupaca (nalaze se na indeksu 1)
    cols = [row[1] for row in c.fetchall()]

    if "lux" not in cols:
        print("[DB] Dodajem stupac 'lux' u tablicu 'logs'...")
        c.execute("ALTER TABLE logs ADD COLUMN lux REAL")

    if "stable" in cols:
        print("[DB] Uklanjam stari stupac 'stable' iz tablice 'logs'...")
        # Najsigurniji način za uklanjanje stupca u SQLite-u
        c.execute("CREATE TABLE logs_new AS SELECT id, timestamp, dht22_air_temp, dht22_humidity, ds18b20_soil_temp, soil_raw, soil_voltage, soil_percent, lux FROM logs")
        c.execute("DROP TABLE logs")
        c.execute("ALTER TABLE logs_new RENAME TO logs")
        print("[DB] Stupac 'stable' uspješno uklonjen.")

    conn.commit()
    conn.close()

# --- Funkcije za rad s logovima senzora ---

def insert_log(timestamp, air_temp, air_humidity, soil_temp, soil_raw, soil_voltage, soil_percent, lux):
    """Upisuje jedan red podataka od senzora u bazu. Sama upravlja konekcijom."""
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
        print(f"[DB ERROR] Neuspješan upis u log: {e}")
    finally:
        conn.close()

def get_logs(limit=100, order="ASC"):
    """Dohvaća zadane logove, sortirane po ID-u."""
    conn = _get_db_connection(dict_cursor=True)
    c = conn.cursor()
    order_clause = "DESC" if order.upper() == "DESC" else "ASC"
    c.execute(f"SELECT * FROM logs ORDER BY id {order_clause} LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_logs_where(where_clause, params=[]):
    """Dohvaća logove koji zadovoljavaju dinamički, ali siguran WHERE uvjet."""
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
    """Briše logove na temelju liste ili stringa ID-eva."""
    if not ids:
        return False, "Nema ID-eva za brisanje."

    try:
        if isinstance(ids, str):
            id_list = [int(x.strip()) for x in ids.split(',') if x.strip().isdigit()]
        elif isinstance(ids, list):
            id_list = [int(x) for x in ids]
        else:
            return False, "Neispravan format ID-eva."
    except ValueError:
        return False, "ID-evi moraju biti brojevi."

    if not id_list:
        return False, "Nema valjanih ID-eva za brisanje."

    conn = _get_db_connection()
    c = conn.cursor()
    placeholders = ",".join("?" for _ in id_list)
    c.execute(f"DELETE FROM logs WHERE id IN ({placeholders})", id_list)
    deleted_count = c.rowcount
    conn.commit()
    conn.close()
    return True, f"Obrisano {deleted_count} zapisa."

# --- Funkcije za rad s logovima releja ---

def insert_relay_event(relay_name, action, source="unknown"):
    """Upisuje ON/OFF događaj releja u bazu."""
    conn = _get_db_connection()
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = "INSERT INTO relay_log (timestamp, relay_name, action, source) VALUES (?, ?, ?, ?)"
    conn.execute(sql, (ts, relay_name, action, source))
    conn.commit()
    conn.close()

def get_relay_log(limit=10):
    """Dohvaća zadnjih N događaja releja."""
    conn = _get_db_connection(dict_cursor=True)
    c = conn.cursor()
    c.execute("SELECT * FROM relay_log ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

# --- Funkcije za administraciju (za manage.py) ---

def get_sql_data():
    """Ispisuje sve retke iz 'logs' tablice na konzolu."""
    conn = _get_db_connection(dict_cursor=True)
    rows = conn.execute("SELECT * FROM logs ORDER BY id").fetchall()
    conn.close()
    for row in rows:
        print(dict(row))

def delete_sql_data(ids=None, delete_all=False):
    """Briše podatke iz 'logs' tablice (namijenjeno za CLI)."""
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