import os
import subprocess
import threading
import time
import atexit

# Moduli projekta
import hardware
import relays
import sensors
import database
from config import BASE_DIR, RELAY1, RELAY2, STATUS_FILE

# Flask
from flask import Flask, render_template, jsonify, request

# --- Inicijalizacija ---
# Inicijaliziraj hardver i bazu podataka prije pokretanja bilo kakve logike
hardware.initialize()
database.init_db()

# Kreiraj Flask aplikaciju
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))

# Postavi da se GPIO resursi očiste pri izlasku iz aplikacije
atexit.register(hardware.cleanup)

# --- Upravljanje logger procesom ---
logger_lock = threading.Lock()
logger_process = None
logger_logfile = os.path.join(BASE_DIR, "logger_run.log")

def is_logger_running():
    """Provjerava radi li logger.py podproces."""
    global logger_process
    if logger_process and logger_process.poll() is None:
        return True
    logger_process = None
    return False

def start_logger():
    """Pokreće logger.py kao podproces."""
    global logger_process
    with logger_lock:
        if is_logger_running():
            return False, "Logger je već pokrenut."

        logger_script = os.path.join(BASE_DIR, "logger.py")
        if not os.path.isfile(logger_script):
            return False, "logger.py skripta nije pronađena."

        # Koristi 'run' naredbu definiranu u logger.py
        cmd = ["python3", logger_script, "run"]
        with open(logger_logfile, "a") as logfile:
            proc = subprocess.Popen(cmd, cwd=BASE_DIR, stdout=logfile, stderr=subprocess.STDOUT)

        logger_process = proc
        time.sleep(0.5) # Daj vremena procesu da se pokrene ili sruši

        if is_logger_running():
            return True, f"Logger pokrenut s PID={proc.pid}."
        else:
            return False, "Neuspješno pokretanje loggera. Provjerite log datoteku."

def stop_logger():
    """Zaustavlja logger.py podproces."""
    global logger_process
    with logger_lock:
        if not is_logger_running():
            return False, "Logger nije bio pokrenut."

        try:
            pid = logger_process.pid
            logger_process.terminate()
            logger_process.wait(timeout=5) # Pričekaj do 5 sekundi
            print(f"Logger proces (PID: {pid}) zaustavljen (terminate).")
        except subprocess.TimeoutExpired:
            logger_process.kill()
            print(f"Logger proces (PID: {pid}) nije odgovarao, poslan kill.")

        logger_process = None
        # Očisti statusnu datoteku
        if os.path.exists(STATUS_FILE):
            os.remove(STATUS_FILE)

        return True, "Logger zaustavljen."

# ---- Rute za stranice (HTML) ----
@app.route("/")
def index():
    # Dohvati zadnjih 50 zapisa za prikaz na početnoj stranici
    # Ova logika će biti premještena u database.py
    logs = database.get_logs(limit=50, order="DESC")
    return render_template("index.html",
                           logs=logs,
                           relay1_state=relays.get_relay_state(RELAY1),
                           relay2_state=relays.get_relay_state(RELAY2),
                           logger_running=is_logger_running())

@app.route("/all_data")
def all_data_page():
    return render_template("all_data.html")

# ---- API Rute ----

@app.route("/api/run/start", methods=["POST"])
def api_run_start():
    ok, msg = start_logger()
    return jsonify({"ok": ok, "msg": msg, "running": is_logger_running()})

@app.route("/api/run/stop", methods=["POST"])
def api_run_stop():
    ok, msg = stop_logger()
    return jsonify({"ok": ok, "msg": msg, "running": is_logger_running()})

@app.route("/api/run/status", methods=["GET"])
def api_run_status():
    running = is_logger_running()
    pid = logger_process.pid if running else None
    return jsonify({"running": running, "pid": pid})

@app.route("/api/logs", methods=["GET"])
def api_logs():
    limit = request.args.get("limit", 100, type=int)
    # Logika će biti prebačena u database.py
    rows = database.get_logs(limit=limit, order="DESC")
    return jsonify(rows)

@app.route("/api/logs/all", methods=["GET"])
def api_logs_all():
    # --- SIGURNOSNI POPRAVAK (SQL Injection) ---
    # Dopušteni stupci za filtriranje kako bi se spriječilo ubacivanje proizvoljnog SQL-a
    allowed_columns = {
        "air_temp": "dht22_air_temp",
        "air_humidity": "dht22_humidity",
        "soil_temp": "ds18b20_soil_temp",
        "soil_percent": "soil_percent",
        "lux": "lux"
    }

    query_params = []
    where_conditions = []

    # Primjer upita: /api/logs/all?lux_gt=100&soil_percent_lt=50
    for key, value in request.args.items():
        parts = key.split('_')
        if len(parts) != 2: continue

        col, op = parts
        if col not in allowed_columns: continue

        operator_map = {"gt": ">", "lt": "<", "eq": "="}
        if op not in operator_map: continue

        db_column = allowed_columns[col]
        operator = operator_map[op]

        where_conditions.append(f"{db_column} {operator} ?")
        query_params.append(value)

    # Ova logika će biti premještena u database.py, ali je ovdje sigurno implementirana
    rows = database.get_logs_where(" AND ".join(where_conditions), query_params)
    return jsonify(rows)

@app.route("/api/logs/delete", methods=["POST"])
def api_logs_delete():
    data = request.json
    ids = data.get("ids")
    # Logika će biti prebačena u database.py
    ok, msg = database.delete_logs_by_id(ids)
    return jsonify({"ok": ok, "msg": msg})

@app.route("/api/sensor/read", methods=["GET"])
def api_sensor_read():
    sensor_type = request.args.get("type", "all")
    try:
        if sensor_type == "ads":
            raw, voltage = sensors.read_soil_raw()
            percent = sensors.read_soil_percent_from_voltage(voltage)
            return jsonify({"type": "ads", "raw": raw, "voltage": voltage, "percent": percent})
        elif sensor_type == "dht":
            temp, hum = sensors.test_dht()
            return jsonify({"type": "dht", "temperature": temp, "humidity": hum})
        elif sensor_type == "ds18b20":
            temp = sensors.read_ds18b20_temp()
            return jsonify({"type": "ds18b20", "temperature": temp})
        elif sensor_type == "bh1750":
            lux = sensors.read_bh1750_lux()
            return jsonify({"type": "bh1750", "lux": lux})
        else:
            return jsonify({"error": "Nepoznat tip senzora"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/relay/toggle", methods=["POST"])
def api_relay_toggle():
    try:
        data = request.get_json()
        relay_num = data.get("relay", type=int)
        state = data.get("state", type=bool)

        pin_map = {1: RELAY1, 2: RELAY2}
        if relay_num not in pin_map:
            return jsonify({"ok": False, "error": "Nepostojeći relej"}), 400

        pin = pin_map[relay_num]
        relay_name = f"RELAY{relay_num}"

        relays.set_relay_state(pin, state)
        database.insert_relay_event(relay_name, "ON" if state else "OFF", source="web")

        print(f"[WEB] Relej {relay_name} prebačen u stanje {'ON' if state else 'OFF'}.")
        return jsonify({"ok": True, "relay": relay_name, "state": "ON" if state else "OFF"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/relay_log", methods=["GET"])
def api_relay_log():
    limit = request.args.get("limit", 10, type=int)
    # Logika će biti prebačena u database.py
    log_data = database.get_relay_log(limit=limit)
    return jsonify(log_data)

@app.route("/logs/file")
def get_logfile():
    """Prikazuje zadnjih 20000 znakova iz log datoteke loggera."""
    if os.path.isfile(logger_logfile):
        try:
            with open(logger_logfile, "r") as f:
                return f"<pre>{f.read()[-20000:]}</pre>"
        except IOError as e:
            return f"Greška pri čitanju log datoteke: {e}"
    return "Log datoteka nije pronađena."


if __name__ == "__main__":
    # Pokreni Flask server na svim mrežnim sučeljima
    app.run(host="0.0.0.0", port=5000, debug=True)