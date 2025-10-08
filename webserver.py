import os
import subprocess
import time
import atexit
import datetime

# Moduli projekta
import hardware
import relays
import sensors
import database
from config import BASE_DIR, RELAY1, RELAY2, STATUS_FILE

# Flask
from flask import Flask, render_template, jsonify, request

# --- Inicijalizacija ---
hardware.initialize()
database.init_db()

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
atexit.register(hardware.cleanup)

logger_logfile = os.path.join(BASE_DIR, "logger_run.log")

# --- Robusno upravljanje logger procesom ---

def is_logger_running():
    """Provjerava radi li logger.py proces koristeći pgrep."""
    try:
        # pgrep -f traži po cijeloj komandnoj liniji
        result = subprocess.run(['pgrep', '-f', 'python3 logger.py'], stdout=subprocess.PIPE)
        return result.returncode == 0
    except FileNotFoundError:
        return False # pgrep nije instaliran

def start_logger():
    """Pokreće logger.py ako već nije pokrenut."""
    if is_logger_running():
        return False, "Logger je već pokrenut."

    logger_script = os.path.join(BASE_DIR, "logger.py")
    if not os.path.isfile(logger_script):
        return False, "logger.py skripta nije pronađena."

    with open(logger_logfile, "a") as logfile:
        subprocess.Popen(["python3", logger_script], cwd=BASE_DIR, stdout=logfile, stderr=subprocess.STDOUT)

    time.sleep(0.5)
    if is_logger_running():
        return True, "Logger uspješno pokrenut."
    else:
        return False, "Neuspješno pokretanje loggera."

def stop_logger():
    """Zaustavlja logger.py proces koristeći pkill."""
    if not is_logger_running():
        return False, "Logger nije bio pokrenut."

    try:
        # pkill -f traži po cijeloj komandnoj liniji i šalje SIGTERM
        subprocess.run(['pkill', '-f', 'python3 logger.py'])
        time.sleep(0.5)
        if not is_logger_running():
             # Očisti statusnu datoteku nakon uspješnog zaustavljanja
            if os.path.exists(STATUS_FILE):
                os.remove(STATUS_FILE)
            return True, "Logger uspješno zaustavljen."
        else:
            return False, "Neuspješno zaustavljanje loggera."
    except FileNotFoundError:
        return False, "pkill naredba nije dostupna."


# ---- Rute za stranice (HTML) ----
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/all_data")
def all_data_page():
    return render_template("all_data.html")

# ---- API Rute ----

@app.route("/api/run/start_first", methods=["POST"])
def api_run_start_first():
    ok, msg = start_logger()
    return jsonify({"ok": ok, "msg": msg, "running": is_logger_running()})

@app.route("/api/run/stop", methods=["POST"])
def api_run_stop():
    ok, msg = stop_logger()
    return jsonify({"ok": ok, "msg": msg, "running": is_logger_running()})

@app.route("/api/status")
def api_status():
    if is_logger_running():
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, "r") as f:
                return {"status": f.read().strip()}
        return {"status": "RUNNING (statusna datoteka nedostaje)"}
    else:
        return {"status": "Logger nije pokrenut"}

@app.route("/api/logs", methods=["GET"])
def api_logs():
    limit = request.args.get("limit", 100, type=int)
    rows = database.get_logs(limit=limit, order="ASC")
    return jsonify(rows)

@app.route("/api/logs/all")
def api_logs_all():
    # ... (logika ostaje ista)
    allowed_columns = {
        "air_temp": "dht22_air_temp", "air_humidity": "dht22_humidity",
        "soil_temp": "ds18b20_soil_temp", "soil_percent": "soil_percent", "lux": "lux",
        "stable": "stable"
    }
    query_params = []
    where_conditions = []

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

    rows = database.get_logs_where(" AND ".join(where_conditions), query_params)
    return jsonify(rows)

@app.route("/api/relay/toggle", methods=["POST"])
def api_relay_toggle():
    # ... (logika ostaje ista)
    try:
        data = request.get_json(force=True)
        if not data or 'relay' not in data or 'state' not in data:
            return jsonify({"ok": False, "error": "Nedostaju 'relay' ili 'state' podaci"}), 400

        relay_num = int(data["relay"])
        state = bool(data["state"])

        pin_map = {1: RELAY1, 2: RELAY2}
        if relay_num not in pin_map:
            return jsonify({"ok": False, "error": "Nepostojeći relej"}), 400

        pin = pin_map[relay_num]
        relay_name = f"RELAY{relay_num}"

        relays.set_relay_state(pin, state)
        database.insert_relay_event(relay_name, "ON" if state else "OFF", source="web")

        return jsonify({"ok": True, "relay": relay_name, "state": "ON" if state else "OFF"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/relay_log_data")
def relay_log_data():
    log_data = database.get_relay_log(limit=15) # <<< SMANJEN LIMIT NA 15

    chart_data = {"RELAY1": [], "RELAY2": []}
    table_data = []

    for entry in log_data:
        table_entry = {
            "t": datetime.datetime.strptime(entry['timestamp'], "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M:%S"),
            "relay": entry['relay_name'],
            "action": entry['action'],
            "source": entry['source'],
            "v": 1 if entry['action'] == 'ON' else 0
        }
        table_data.append(table_entry)

    for entry in reversed(log_data):
        chart_ts = datetime.datetime.strptime(entry['timestamp'], "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
        chart_item = {"t": chart_ts, "v": 1 if entry['action'] == 'ON' else 0}
        if entry['relay_name'] == 'RELAY1':
            chart_data['RELAY1'].append(chart_item)
        elif entry['relay_name'] == 'RELAY2':
            chart_data['RELAY2'].append(chart_item)

    return jsonify({
        "chart_data": chart_data,
        "table_data": table_data
    })

@app.route("/logs/file")
def get_logfile():
    if os.path.isfile(logger_logfile):
        try:
            with open(logger_logfile, "r") as f:
                return f"<pre>{f.read()[-20000:]}</pre>"
        except IOError as e:
            return f"Greška pri čitanju log datoteke: {e}"
    return "Log datoteka nije pronađena."


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False) # Debug mode is OFF for stability