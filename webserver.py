import os
import sqlite3
import subprocess
import threading
import time
from typing import List, Dict, Any, Tuple, Optional
import datetime

import relays
import config
from flask import Flask, render_template, jsonify, request

from config import BASE_DIR, DB_FILE, RELAY1, RELAY2
from relays import get_relay_state
import sensors
from sensors import read_bh1750_lux

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))

logger_lock = threading.Lock()
logger_process: Optional[subprocess.Popen] = None
logger_logfile = os.path.join(BASE_DIR, "logger_run.log")


def is_logger_running() -> bool:
    """Checks if the logger subprocess is currently running."""
    global logger_process
    if logger_process is None:
        return False
    if logger_process.poll() is None:
        return True
    logger_process = None
    return False


def start_logger(mode: str = "run") -> Tuple[bool, str]:
    """
    Starts the logger.py script as a subprocess.

    Args:
        mode (str): The mode to pass to logger.py.

    Returns:
        Tuple[bool, str]: A tuple containing a success flag and a message.
    """
    global logger_process
    with logger_lock:
        if is_logger_running():
            return False, "already_running"
        logger_py = os.path.join(BASE_DIR, "logger.py")
        if not os.path.isfile(logger_py):
            return False, f"logger.py not found at {logger_py}"
        cmd = [sys.executable, logger_py, mode]
        logfile = open(logger_logfile, "a")
        proc = subprocess.Popen(cmd, cwd=BASE_DIR, stdout=logfile, stderr=logfile)
        logger_process = proc
        time.sleep(0.2)
        if proc.poll() is None:
            return True, f"started pid={proc.pid}"
        else:
            return False, "failed_to_start"


def stop_logger() -> Tuple[bool, str]:
    """Stops the logger subprocess."""
    global logger_process
    with logger_lock:
        if not is_logger_running():
            try:
                with open(config.STATUS_FILE, "w") as f:
                    f.write("STOPPED\n")
            except Exception as e:
                print(f"[WARN] Ne mogu pisati u STATUS_FILE: {e}")
            return False, "not_running"

        try:
            logger_process.terminate()
            for _ in range(10):
                if logger_process.poll() is not None:
                    break
                time.sleep(0.2)
            if logger_process.poll() is None:
                logger_process.kill()

            pid = logger_process.pid
            logger_process = None
            time.sleep(0.1)
            with open(config.STATUS_FILE, "w") as f:
                f.write("-.-")
            return True, f"stopped pid={pid}"
        except Exception as e:
            print(f"[ERROR] stop_logger(): {e}")
            return False, f"error:{e}"


def get_last_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieves the last N log entries from the database."""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, timestamp, dht22_air_temp, dht22_humidity, ds18b20_soil_temp, soil_raw, soil_voltage, soil_percent, lux, stable FROM logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        rows.reverse()
        result = []
        for r in rows:
            result.append({
                "id": r[0], "timestamp": r[1], "air_temp": r[2], "air_humidity": r[3],
                "soil_temp": r[4], "soil_raw": r[5], "soil_voltage": r[6],
                "soil_percent": r[7], "lux": r[8], "stable": r[9]
            })
        conn.close()
        return result
    except Exception:
        return []


@app.route("/")
def index():
    """Renders the main dashboard page."""
    rows = get_last_logs(limit=50)
    return render_template("index.html", logs=rows,
                           relay1=get_relay_state(RELAY1),
                           relay2=get_relay_state(RELAY2),
                           logger_running=is_logger_running())


@app.route("/api/run/start_first", methods=["POST"])
def api_run_start_first():
    ok, msg = start_logger(mode="run_first")
    return jsonify({"ok": ok, "msg": msg, "running": is_logger_running()})


@app.route("/api/run/stop", methods=["POST"])
def api_run_stop():
    ok, msg = stop_logger()
    return jsonify({"ok": ok, "msg": msg, "running": is_logger_running()})


@app.route("/api/run/status", methods=["GET"])
def api_run_status():
    return jsonify({"running": is_logger_running(),
                    "pid": None if logger_process is None else logger_process.pid})


@app.route("/api/logs", methods=["GET"])
def api_logs():
    limit = int(request.args.get("limit", 100))
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT id, timestamp,
               dht22_air_temp AS air_temp,
               dht22_humidity AS air_humidity,
               ds18b20_soil_temp AS soil_temp,
               soil_percent,
               lux,
               stable
        FROM logs
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in c.fetchall()]
    rows.reverse()
    conn.close()
    return jsonify(rows)


@app.route("/api/logs/all")
def api_logs_all():
    where = request.args.get("where", "")
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    query = "SELECT id, timestamp, dht22_air_temp AS air_temp, dht22_humidity AS air_humidity, ds18b20_soil_temp AS soil_temp, soil_percent, lux, stable FROM logs"
    if where:
        query += f" WHERE {where}"
    query += " ORDER BY id ASC"
    try:
        c.execute(query)
        rows = [dict(r) for r in c.fetchall()]
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    conn.close()
    return jsonify(rows)


@app.route("/all_data")
def all_data_page():
    return render_template("all_data.html")


@app.route("/api/sensor/read", methods=["GET"])
def api_sensor_read():
    t = request.args.get("type", "ads")
    try:
        if t == "ads":
            raw, voltage = sensors.read_soil_raw()
            pct = sensors.read_soil_percent(voltage=voltage)
            return jsonify({"type": "ads", "raw": raw, "voltage": voltage, "percent": pct})
        elif t == "dht":
            temp, hum = sensors.test_dht()
            return jsonify({"type": "dht", "temperature": temp, "humidity": hum})
        elif t == "ds18b20":
            temp = sensors.test_ds18b20()
            return jsonify({"type": "ds18b20", "temperature": temp})
        elif t == "bh1750":
            lux = read_bh1750_lux()
            return jsonify({"type": "bh1750", "lux": lux})
        else:
            return jsonify({"error": "unknown sensor type"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/relay/toggle", methods=["POST"])
def api_relay_toggle():
    try:
        data = request.get_json(force=True)
        relay_num = int(data.get("relay"))
        state = bool(data.get("state"))
        relay_name = f"RELAY{relay_num}"
        relay_pin = getattr(config, relay_name)
        relays.set_relay_state(relay_pin, state)
        import database
        database.insert_relay_event(relay_name, "ON" if state else "OFF", source="button")
        print(f"[LOG] {relay_name} -> {'ON' if state else 'OFF'} (ručno putem web sučelja)")
        return jsonify({"ok": True, "relay": relay_name, "state": "ON" if state else "OFF"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/logs/file")
def get_logfile():
    if os.path.isfile(logger_logfile):
        with open(logger_logfile, "r") as f:
            return "<pre>" + f.read()[-20000:] + "</pre>"
    return "No logfile found."


@app.route("/api/logs/delete", methods=["POST"])
def api_logs_delete():
    data = request.json
    ids = data.get("ids", "")
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        if isinstance(ids, str) and ids.strip().lower() == "all":
            c.execute("DELETE FROM logs")
            conn.commit()
            deleted = "all"
        else:
            id_list = []
            for part in ids.split(','):
                part = part.strip()
                if '-' in part:
                    start, end = part.split('-')
                    id_list.extend(range(int(start), int(end) + 1))
                else:
                    id_list.append(int(part))

            if not id_list:
                return jsonify({"ok": False, "msg": "Nema ID-eva za brisanje"}), 400
            placeholders = ",".join("?" for _ in id_list)
            c.execute(f"DELETE FROM logs WHERE id IN ({placeholders})", id_list)
            conn.commit()
            deleted = len(id_list)
        conn.close()
        return jsonify({"ok": True, "deleted": deleted})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/toggle_relay/<relay_id>", methods=["POST"])
def toggle_relay(relay_id: str):
    state = request.form.get("state")
    relay_pin = getattr(config, relay_id)
    relays.set_relay_state(relay_pin, state == "ON")
    try:
        import database
        database.insert_relay_event(relay_id, state, source="button")
        print(f"[LOG] Relej {relay_id} -> {state}")
    except Exception as e:
        print(f"[WARN] Relay log upis nije uspio: {e}")
    return jsonify({"ok": True, "relay": relay_id, "state": state})


@app.route("/relay_log_data")
def relay_log_data():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT timestamp, relay_name, action FROM relay_log ORDER BY timestamp DESC LIMIT 10")
    rows = cur.fetchall()
    conn.close()
    data = []
    for ts, relay, action in rows:
        try:
            t = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M:%S")
            value = 1 if action.upper() == "ON" else 0
            data.append({"t": t, "relay": relay.upper(), "v": value, "action": action.upper()})
        except Exception as e:
            print(f"[WARN] relay_log_data parse error: {e}")
    return jsonify(data)


@app.route("/api/status")
def api_status():
    if os.path.exists(config.STATUS_FILE):
        with open(config.STATUS_FILE, "r") as f:
            content = f.read().strip()
        return {"status": content}
    else:
        return {"status": "Logger nije pokrenut"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
