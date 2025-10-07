#database.py
import sqlite3
import datetime
from config import DB_FILE

def init_db():
    """Kreira bazu i tablicu logs ako ne postoji. Dodaje lux stupac ako fali."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Kreiraj tablicu ako ne postoji
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
    conn.commit()

    # Provjeri postoji li stupac 'lux'
    c.execute("PRAGMA table_info(logs)")
    cols = [row[1] for row in c.fetchall()]
    if "lux" not in cols:
        print("[DB] Dodajem stupac 'lux' u tablicu logs...")
        c.execute("ALTER TABLE logs ADD COLUMN lux REAL")
        conn.commit()
    if "stable" not in cols:
            print("[DB] Dodajem stupac 'stable' u tablicu logs...")
            c.execute("ALTER TABLE logs ADD COLUMN stable INTEGER DEFAULT 1;")
            conn.commit()
    return conn

def delete_sql_data(ids=None, delete_all=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    if delete_all:
        confirm = input("⚠️  Sigurno želiš obrisati SVE podatke iz baze? (yes/no): ")
        if confirm.lower() == "yes":
            c.execute("DELETE FROM logs")
            c.execute("DELETE FROM sqlite_sequence WHERE name='logs'")  # reset autoincrement
            conn.commit()
            print("✅ Svi zapisi obrisani i indeks resetiran.")
        else:
            print("❌ Otkazano brisanje svih zapisa.")
    elif ids:
        try:
            id_list = []
            for part in ids.split(","):
                part = part.strip()
                if "-" in part:
                    start, end = part.split("-")
                    start, end = int(start), int(end)
                    id_list.extend(range(start, end + 1))
                else:
                    id_list.append(int(part))

            id_list = sorted(set(id_list))
            placeholders = ",".join("?" for _ in id_list)
            c.execute(f"DELETE FROM logs WHERE id IN ({placeholders})", id_list)
            conn.commit()
            print(f"✅ Obrisani zapisi s ID-evima: {id_list}")
        except ValueError:
            print("❌ Greška: ID-evi moraju biti brojevi, npr. 1,3,5 ili 3-10.")
    else:
        print("⚠️ Nisi naveo ni --all ni --ids za brisanje.")

    conn.close()

def get_sql_data():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM logs")
    rows = c.fetchall()
    for row in rows:
        print(row)
    conn.close()

# ------------------ RELAY LOG ------------------
def ensure_relay_log_table():
    """Osigurava da relay_log tablica postoji."""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS relay_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            relay_name TEXT,
            action TEXT,
            source TEXT
        )
    """)
    conn.commit()
    conn.close()

def insert_relay_event(relay_name, action, source="button"):
    """Upisuje ON/OFF događaj u relay_log tablicu."""
    ensure_relay_log_table()
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "INSERT INTO relay_log (timestamp, relay_name, action, source) VALUES (?, ?, ?, ?)",
        (ts, relay_name, action, source)
    )
    conn.commit()
    conn.close()
