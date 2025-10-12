import os
import subprocess
import threading
import time
import atexit

# Project modules
import hardware
import relays
import sensors
import database
from config import BASE_DIR, RELAY1, RELAY2, STATUS_FILE
import process_manager

# Flask
from flask import Flask, render_template, jsonify, request

# Create Flask application
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))


# --- Startup initialization (deferred) ---
@app.before_first_request
def _app_startup():
    """Initialize hardware and database at runtime.

    This avoids side-effects at import time (useful for analysis, tests,
    and CI on non-RPi hosts). It also registers cleanup for atexit.
    """
    try:
        hardware.initialize()
    except Exception as e:
        print(f"[WARN] hardware.initialize() failed during startup: {e}")

    try:
        database.init_db()
    except Exception as e:
        print(f"[WARN] database.init_db() failed during startup: {e}")

    # Register cleanup after successful (or attempted) initialization
    atexit.register(hardware.cleanup)

# --- Logger Process Management (delegated) ---
_logger_mgr = process_manager.init_logger_manager(BASE_DIR)

def is_logger_running():
    mgr = process_manager.get_logger_manager()
    return mgr.is_running() if mgr else False

def start_logger():
    mgr = process_manager.get_logger_manager()
    if not mgr:
        return False, "Logger manager not initialized."
    return mgr.start()

def stop_logger():
    mgr = process_manager.get_logger_manager()
    if not mgr:
        return False, "Logger manager not initialized."
    ok, msg = mgr.stop()
    # Clean up the status file
    if os.path.exists(STATUS_FILE):
        try:
            os.remove(STATUS_FILE)
        except Exception:
            pass
    return ok, msg

# ---- HTML Page Routes ----
@app.route("/")
def index():
    """Renders the main dashboard page.

    Fetches the last 50 log entries and current relay states to display.

    Returns:
        The rendered index.html template.
    """
    logs = database.get_logs(limit=50, order="DESC")
    return render_template("index.html",
                           logs=logs,
                           relay1_state=relays.get_relay_state(RELAY1),
                           relay2_state=relays.get_relay_state(RELAY2),
                           logger_running=is_logger_running())

@app.route("/all_data")
def all_data_page():
    """Renders the page for viewing all data."""
    return render_template("all_data.html")

# ---- API Routes ----

@app.route("/api/run/start_first", methods=["POST"])
def api_run_start():
    """API endpoint to start the logger process."""
    ok, msg = start_logger()
    return jsonify({"ok": ok, "msg": msg, "running": is_logger_running()})

@app.route("/api/run/stop", methods=["POST"])
def api_run_stop():
    """API endpoint to stop the logger process."""
    ok, msg = stop_logger()
    return jsonify({"ok": ok, "msg": msg, "running": is_logger_running()})

@app.route("/api/status", methods=["GET"])
def api_run_status():
    """API endpoint to get the status of the logger process."""
    running = is_logger_running()
    pid = logger_process.pid if running else None
    status_text = f"RUNNING @ {time.strftime('%d.%m.%Y %H:%M:%S')} (PID: {pid})" if running else "STOPPED"
    return jsonify({"status": status_text})

@app.route("/api/logs", methods=["GET"])
def api_logs():
    """API endpoint to get the latest sensor logs.

    Query Parameters:
        limit (int): The number of logs to return. Defaults to 100.

    Returns:
        A JSON response with a list of log entries.
    """
    limit = request.args.get("limit", 100, type=int)
    rows = database.get_logs(limit=limit, order="DESC")
    return jsonify(rows)

@app.route("/api/logs/all", methods=["GET"])
def api_logs_all():
    """API endpoint to get all logs with optional filtering.

    This endpoint allows filtering by sensor values using query parameters like
    `lux_gt=100` or `soil_percent_lt=50`.

    Returns:
        A JSON response with a list of filtered log entries.
    """
    allowed_columns = {
        "air_temp": "dht22_air_temp",
        "air_humidity": "dht22_humidity",
        "soil_temp": "ds18b20_soil_temp",
        "soil_percent": "soil_percent",
        "lux": "lux"
    }

    query_params = []
    where_conditions = []

    # Example query: /api/logs/all?lux_gt=100&soil_percent_lt=50
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

@app.route("/api/logs/delete", methods=["POST"])
def api_logs_delete():
    """API endpoint to delete log entries by their IDs."""
    data = request.json
    ids = data.get("ids")
    ok, msg = database.delete_logs_by_id(ids)
    return jsonify({"ok": ok, "msg": msg})

@app.route("/api/sensor/read", methods=["GET"])
def api_sensor_read():
    """API endpoint to read a single value from a specified sensor.

    Query Parameters:
        type (str): The type of sensor to read ('ads', 'dht', 'ds18b20', 'bh1750').

    Returns:
        A JSON response with the sensor reading, or an error.
    """
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
            return jsonify({"error": "Unknown sensor type"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/relay/toggle", methods=["POST"])
def api_relay_toggle():
    """API endpoint to toggle the state of a relay."""
    try:
        data = request.get_json()
        print(f"Received relay toggle request: {data}")  # Debugging line
        relay_num = data.get("relay")
        state = data.get("state")

        # Basic validation
        if relay_num not in [1, 2] or not isinstance(state, bool):
            return jsonify({"ok": False, "error": "Invalid input"}), 400

        pin_map = {1: RELAY1, 2: RELAY2}
        pin = pin_map[relay_num]
        relay_name = f"RELAY{relay_num}"

        relays.set_relay_state(pin, state)
        database.insert_relay_event(relay_name, "ON" if state else "OFF", source="web")

        print(f"[WEB] Relay {relay_name} switched to {'ON' if state else 'OFF'}.")
        return jsonify({"ok": True, "relay": relay_name, "state": "ON" if state else "OFF"})
    except Exception as e:
        print(f"[ERROR] api_relay_toggle failed: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/relay_log_data", methods=["GET"])
def api_relay_log():
    """API endpoint to get the latest relay event logs.

    Query Parameters:
        limit (int): The number of logs to return. Defaults to 10.
    """
    limit = request.args.get("limit", 10, type=int)
    log_data = database.get_relay_log(limit=limit)

    # The frontend expects a different format, so we transform the data here
    transformed_data = {"RELAY1": [], "RELAY2": []}
    for row in log_data:
        relay_name = row['relay_name']
        if relay_name in transformed_data:
            transformed_data[relay_name].append({
                "t": row['timestamp'].split(" ")[1],
                "v": 1 if row['action'] == 'ON' else 0,
                "action": row['action'],
                "source": row['source']
            })
    return jsonify(transformed_data)

@app.route("/logs/file")
def get_logfile():
    """Displays the last 20000 characters from the logger's log file."""
    if os.path.isfile(logger_logfile):
        try:
            with open(logger_logfile, "r") as f:
                return f"<pre>{f.read()[-20000:]}</pre>"
        except IOError as e:
            return f"Error reading log file: {e}"
    return "Log file not found."


if __name__ == "__main__":
    # Run the Flask server on all network interfaces
    app.run(host="0.0.0.0", port=5000, debug=True)