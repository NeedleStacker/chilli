import os
import subprocess
import threading
import time
import atexit
import datetime

# Moduli projekta
import hardware
import relays
import sensors
import database
from config import BASE_DIR, RELAY1, RELAY2, STATUS_FILE, PID_FILE

# Flask
from flask import Flask, render_template, jsonify, request

# --- Inicijalizacija ---
hardware.initialize()
database.init_db()

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
atexit.register(hardware.cleanup)

# --- Pouzdano upravljanje logger procesom (vraćeno na jednostavniju logiku) ---
logger_lock = threading.Lock()
logger_process = None
logger_logfile = os.path.join(BASE_DIR, "logger_run.log")

def is_logger_running():
    """Provjerava radi li logger.py podproces čitanjem PID datoteke."""
    if not os.path.exists(PID_FILE):
        return False
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        # Provjera postoji li proces s tim PID-om.
        # os.kill(pid, 0) baca OSError ako proces ne postoji.
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        # Ako proces ne postoji ili PID datoteka nije ispravna,
        # smatramo da logger nije pokrenut i brišemo datoteku.
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
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

        # Brišemo stari log pri svakom novom pokretanju radi čistoće
        if os.path.exists(logger_logfile):
            os.remove(logger_logfile)

        with open(logger_logfile, "a") as logfile:
            proc = subprocess.Popen(["python3", logger_script], cwd=BASE_DIR, stdout=logfile, stderr=subprocess.STDOUT)

        logger_process = proc
        time.sleep(0.5)

        if is_logger_running():
            return True, f"Logger pokrenut s PID={proc.pid}."
        else:
            return False, "Neuspješno pokretanje loggera."

def stop_logger():
    """Zaustavlja logger.py podproces."""
    global logger_process
    with logger_lock:
        if not is_logger_running():
            return False, "Logger nije bio pokrenut."

        try:
            pid = logger_process.pid
            logger_process.terminate()
            logger_process.wait(timeout=5)
            print(f"Logger proces (PID: {pid}) zaustavljen (terminate).")
        except (subprocess.TimeoutExpired, AttributeError):
             print("Logger proces nije odgovarao ili je već ugašen.")

        logger_process = None
        if os.path.exists(STATUS_FILE):
            os.remove(STATUS_FILE)

        return True, "Logger zaustavljen."

# ---- Rute za stranice (HTML) ----
@app.route("/")
def index():
    # Dohvati početno stanje releja i loggera i proslijedi ih u predložak
    relay1_state = relays.get_relay_state(RELAY1)
    relay2_state = relays.get_relay_state(RELAY2)
    return render_template("index.html",
                           logger_running=is_logger_running(),
                           relay1=relay1_state,
                           relay2=relay2_state)

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
        return {"status": f"RUNNING (PID: {logger_process.pid if logger_process else 'unknown'})"}
    else:
        return {"status": "Logger nije pokrenut"}

@app.route("/api/logs", methods=["GET"])
def api_logs():
    limit = request.args.get("limit", 100, type=int)
    rows = database.get_logs(limit=limit, order="ASC")
    return jsonify(rows)

@app.route("/api/logs/all")
def api_logs_all():
    allowed_columns = {
        "air_temp": "dht22_air_temp", "air_humidity": "dht22_humidity",
        "soil_temp": "ds18b20_soil_temp", "soil_percent": "soil_percent", "lux": "lux",
        "stable": "stable"
    }
    query_params = []
    where_conditions = []

    where_str = request.args.get("where", "")
    if where_str:
        parts = where_str.split()
        if len(parts) == 3 and parts[0] in allowed_columns:
            db_column = allowed_columns[parts[0]]
            operator = parts[1]
            value = parts[2]
            if operator in ['>', '<', '=', '>=', '<=']:
                 where_conditions.append(f"{db_column} {operator} ?")
                 query_params.append(value)

    where_clause = " AND ".join(where_conditions)
    rows = database.get_logs_where(where_clause, query_params)
    return jsonify(rows)


@app.route("/api/logs/delete", methods=["POST"])
def api_logs_delete():
    data = request.json
    ids = data.get("ids")
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
    log_data = database.get_relay_log(limit=15)

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
    # use_reloader=False je ključno za stabilno stanje logger_process varijable
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)