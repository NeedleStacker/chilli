import sys
import fake_rpi

sys.modules['RPi'] = fake_rpi.RPi
sys.modules['RPi.GPIO'] = fake_rpi.RPi.GPIO
sys.modules['smbus'] = fake_rpi.smbus

import os
import sqlite3
import subprocess
import threading
import time
import relays
import config
import database
import sensors
import datetime

from flask import Flask, render_template, jsonify, request
from config import BASE_DIR, DATABASE_FILE, RELAY1_PIN, RELAY2_PIN
from relays import get_relay_state, set_relay_state

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))

logger_lock = threading.Lock()
logger_process = None
logger_logfile = os.path.join(BASE_DIR, "logger_run.log")

# --- Logger Subprocess Management ---

def is_logger_running() -> bool:
    """Checks if the logger subprocess is currently running."""
    global logger_process
    if logger_process is None:
        return False
    if logger_process.poll() is None:
        return True
    logger_process = None  # Process has finished
    return False

def start_logger(mode: str = "run") -> tuple[bool, str]:
    """
    Starts the logger.py script as a subprocess.

    Args:
        mode (str): The mode to pass to logger.py (e.g., 'run', 'run_shared_i2c').

    Returns:
        tuple[bool, str]: A tuple containing a success flag and a message.
    """
    global logger_process
    with logger_lock:
        if is_logger_running():
            return False, "Logger is already running."

        logger_script_path = os.path.join(BASE_DIR, "logger.py")
        if not os.path.isfile(logger_script_path):
            return False, f"logger.py not found at {logger_script_path}"

        command = [sys.executable, logger_script_path, mode]
        try:
            logfile = open(logger_logfile, "a")
            proc = subprocess.Popen(command, cwd=BASE_DIR, stdout=logfile, stderr=logfile)
            logger_process = proc
            time.sleep(0.2)  # Give it a moment to start
            if proc.poll() is None:
                return True, f"Logger started with PID: {proc.pid}"
            else:
                return False, "Failed to start logger process."
        except (IOError, OSError) as e:
            return False, f"Error starting logger: {e}"

def stop_logger() -> tuple[bool, str]:
    """Stops the logger subprocess."""
    global logger_process
    with logger_lock:
        if not is_logger_running():
            try:
                with open(config.STATUS_FILE, "w") as f:
                    f.write("STOPPED\n")
            except IOError as e:
                print(f"[Warning] Could not write to status file: {e}")
            return False, "Logger is not running."

        try:
            pid = logger_process.pid
            logger_process.terminate()
            logger_process.wait(timeout=2)  # Wait for graceful termination
        except (ProcessLookupError, subprocess.TimeoutExpired):
            logger_process.kill()  # Force kill if it doesn't terminate
        finally:
            logger_process = None

        try:
            with open(config.STATUS_FILE, "w") as f:
                f.write("STOPPED")
        except IOError as e:
            print(f"[Warning] Could not update status file: {e}")

        return True, f"Logger process (PID: {pid}) stopped."

# --- Database Helper ---

def get_latest_logs(limit: int = 100) -> list[dict]:
    """Retrieves the last N log entries from the database."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, timestamp, dht22_air_temp, dht22_humidity, ds18b20_soil_temp, "
            "soil_raw, soil_voltage, soil_percent, lux, stable "
            "FROM logs ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
        conn.close()
        # Convert rows to dicts and reverse to have the oldest first
        return [dict(row) for row in reversed(rows)]
    except sqlite3.Error as e:
        print(f"[Error] Database query failed: {e}")
        return []

# --- Flask Routes ---

@app.route("/")
def index():
    """Renders the main dashboard page."""
    latest_logs = get_latest_logs(limit=50)
    return render_template(
        "index.html",
        logs=latest_logs,
        relay1_state=get_relay_state(RELAY1_PIN),
        relay2_state=get_relay_state(RELAY2_PIN),
        is_logger_running=is_logger_running(),
    )

@app.route("/api/run/start_first", methods=["POST"])
def api_run_start_first():
    ok, msg = start_logger(mode="run_first")
    return jsonify({"ok": ok, "msg": msg, "running": is_logger_running()})


@app.route("/api/run/stop", methods=["POST"])
def api_run_stop():
    ok, msg = stop_logger()
    return jsonify({"ok": ok, "msg": msg, "running": is_logger_running()})

@app.route("/api/run/status", methods=["GET"])
def api_logger_status():
    """API endpoint to get the logger's running status."""
    return jsonify({
        "is_running": is_logger_running(),
        "pid": logger_process.pid if logger_process else None,
    })

@app.route("/api/logs", methods=["GET"])
def api_get_logs():
    """API endpoint to get a list of logs."""
    limit = int(request.args.get("limit", 100))
    logs = get_latest_logs(limit=limit)
    # Map keys to what the frontend expects
    mapped_logs = []
    for log in logs:
        mapped_logs.append({
            "id": log["id"],
            "timestamp": log["timestamp"],
            "air_temp": log["dht22_air_temp"],
            "air_humidity": log["dht22_humidity"],
            "soil_temp": log["ds18b20_soil_temp"],
            "soil_percent": log["soil_percent"],
            "lux": log["lux"],
            "stable": log["stable"]
        })
    return jsonify(mapped_logs)

@app.route("/api/logs/all", methods=["GET"])
def api_logs_all():
    """API endpoint to query logs with a WHERE clause."""
    where_clause = request.args.get("where", "")
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = "SELECT id, timestamp, dht22_air_temp as air_temp, dht22_humidity as air_humidity, ds18b20_soil_temp as soil_temp, soil_percent, lux, stable FROM logs"
        if where_clause:
            query += f" WHERE {where_clause}"
        query += " ORDER BY id ASC"
        cursor.execute(query)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(rows)
    except sqlite3.Error as e:
        return jsonify({"ok": False, "error": str(e)}), 400

@app.route("/all_data")
def all_data_page():
    """Renders the page for viewing all historical data."""
    return render_template("all_data.html")

@app.route("/api/sensor/read", methods=["GET"])
def api_read_sensor():
    """API endpoint to read a single sensor on demand."""
    sensor_type = request.args.get("type", "ads")
    try:
        if sensor_type == "ads":
            raw, voltage = sensors.read_soil_moisture_raw()
            percent = sensors.convert_voltage_to_soil_percentage(voltage)
            return jsonify({"type": "ads", "raw": raw, "voltage": voltage, "percent": percent})
        elif sensor_type == "dht":
            temp, hum = sensors.read_dht22_sensor()
            return jsonify({"type": "dht", "temperature": temp, "humidity": hum})
        elif sensor_type == "ds18b20":
            temp = sensors.read_ds18b20_temperature()
            return jsonify({"type": "ds18b20", "temperature": temp})
        elif sensor_type == "bh1750":
            lux = sensors.read_bh1750_light_intensity()
            return jsonify({"type": "bh1750", "lux": lux})
        else:
            return jsonify({"error": "Unknown sensor type"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/relay/toggle", methods=["POST"])
def api_toggle_relay():
    """API endpoint to toggle a relay's state."""
    try:
        data = request.get_json(force=True)
        relay_num = int(data.get("relay"))
        state = bool(data.get("state"))

        relay_name = f"RELAY{relay_num}"
        relay_pin = getattr(config, f"{relay_name}_PIN")

        set_relay_state(relay_pin, state)
        action = "ON" if state else "OFF"
        database.insert_relay_log_event(relay_name, action, source="web_ui")

        print(f"[WebUI] Toggled {relay_name} -> {action}")
        return jsonify({"ok": True, "relay": relay_name, "state": action})
    except (AttributeError, TypeError, ValueError) as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/logs/file")
def view_logfile():
    """Displays the content of the logger's log file."""
    if os.path.isfile(logger_logfile):
        with open(logger_logfile, "r") as f:
            return f"<pre>{f.read()[-20000:]}</pre>"
    return "Log file not found."

@app.route("/api/logs/delete", methods=["POST"])
def api_delete_logs():
    """API endpoint to delete log records."""
    data = request.json
    ids_to_delete = data.get("ids")

    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        if isinstance(ids_to_delete, str) and ids_to_delete.strip().lower() == "all":
            cursor.execute("DELETE FROM logs")
            deleted_count = "all"
        elif isinstance(ids_to_delete, (list, str)):
            if isinstance(ids_to_delete, str):
                id_list = [int(x.strip()) for x in ids_to_delete.split(",") if x.strip().isdigit()]
            else:
                id_list = [int(x) for x in ids_to_delete]

            if not id_list:
                return jsonify({"ok": False, "message": "No valid IDs provided"}), 400

            placeholders = ",".join("?" for _ in id_list)
            cursor.execute(f"DELETE FROM logs WHERE id IN ({placeholders})", id_list)
            deleted_count = cursor.rowcount
        else:
            return jsonify({"ok": False, "message": "Invalid ID format"}), 400

        conn.commit()
        conn.close()
        return jsonify({"ok": True, "deleted_count": deleted_count})
    except (sqlite3.Error, ValueError) as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/toggle_relay/<relay_id>", methods=["POST"])
def toggle_relay(relay_id):
    state = request.form.get("state")  # "ON" ili "OFF"
    relay_pin = getattr(config, relay_id)
    set_relay_state(relay_pin, state == "ON")

    # Upis događaja u relay_log tablicu
    try:
        database.insert_relay_log_event(relay_id, state, source="button")
        print(f"[LOG] Relej {relay_id} -> {state}")
    except Exception as e:
        print(f"[WARN] Relay log upis nije uspio: {e}")

    return jsonify({"ok": True, "relay": relay_id, "state": state})


@app.route("/relay_log_data", methods=["GET"])
def relay_log_data():
    """API endpoint to retrieve the latest relay log events."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, relay_name, action, source FROM relay_log ORDER BY timestamp DESC LIMIT 10")
        rows = cursor.fetchall()
        conn.close()

        log_data = []
        for ts, relay, action, source in rows:
            formatted_ts = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M:%S")
            log_data.append({
                "t": formatted_ts,
                "relay": relay.upper(),
                "action": action.upper(),
                "v": 1 if action.upper() == "ON" else 0,
                "source": source
            })
        return jsonify(log_data)
    except (sqlite3.Error, ValueError) as e:
        print(f"[Warning] Could not parse relay log data: {e}")
        return jsonify([])

@app.route("/api/status")
def api_get_status():
    """API endpoint to get the logger's status from the status file."""
    if os.path.exists(config.STATUS_FILE):
        with open(config.STATUS_FILE, "r") as f:
            content = f.read().strip()
        return jsonify({"status": content})
    else:
        return jsonify({"status": "Logger not running"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
