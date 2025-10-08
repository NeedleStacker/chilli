import time
import datetime
import os
import signal

# Moduli projekta
import hardware
import database
import sensors
from relays import set_relay_state
from config import (
    LOGS_DIR, STATUS_FILE, LAST_WATERING_FILE,
    LOG_INTERVAL_SECONDS, WATERING_THRESHOLD_PERCENT,
    WATERING_DURATION_SECONDS, WATERING_COOLDOWN_SECONDS,
    RELAY1
)

def cleanup():
    """Čisti statusnu datoteku pri gašenju."""
    print("Čistim status datoteku...")
    if os.path.exists(STATUS_FILE):
        os.remove(STATUS_FILE)

def handle_signal(signum, frame):
    """Handler za signale (npr. SIGTERM) za sigurno gašenje."""
    print(f"Primljen signal {signum}, gasim se...")
    exit(0)

# Registriraj handlere za sigurno gašenje
signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


def should_water(soil_percent):
    """Provjerava treba li pokrenuti automatsko zalijevanje."""
    if soil_percent is None: return False
    if soil_percent >= WATERING_THRESHOLD_PERCENT: return False
    if os.path.exists(LAST_WATERING_FILE):
        try:
            with open(LAST_WATERING_FILE, "r") as f: last_ts = float(f.read().strip())
            if time.time() - last_ts < WATERING_COOLDOWN_SECONDS:
                return False
        except (ValueError, IOError):
            pass
    return True


def perform_watering():
    """Aktivira relej pumpe za vodu i bilježi vrijeme."""
    print(f"[AUTO] Uključujem pumpu na {WATERING_DURATION_SECONDS}s ...")
    try:
        set_relay_state(RELAY1, True)
        database.insert_relay_event("RELAY1", "ON", source="auto")
        time.sleep(WATERING_DURATION_SECONDS)
    finally:
        set_relay_state(RELAY1, False)
        database.insert_relay_event("RELAY1", "OFF", source="auto")
    try:
        with open(LAST_WATERING_FILE, "w") as f: f.write(str(time.time()))
    except IOError as e:
        print(f"[ERROR] Nije moguće zapisati vrijeme zadnjeg zalijevanja: {e}")
    print("[AUTO] Zalijevanje završeno.")


def run_logger():
    """Glavna petlja za periodično očitavanje senzora i upis u bazu."""
    pid = os.getpid()
    print(f"Logger se pokreće s PID: {pid}...")
    database.init_db()
    os.makedirs(LOGS_DIR, exist_ok=True)

    try:
        while True:
            with open(STATUS_FILE, "w") as f:
                f.write(f"RUNNING @ {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')} (PID: {pid})")

            # --- Očitavanje senzora ---
            try: lux = sensors.read_bh1750_lux()
            except Exception as e: print(f"[ERROR] BH1750: {e}"); lux = None
            try:
                soil_raw, soil_voltage = sensors.read_soil_raw()
                soil_percent = sensors.read_soil_percent_from_voltage(soil_voltage)
            except Exception as e: print(f"[ERROR] ADS1115: {e}"); soil_raw, soil_voltage, soil_percent = None, None, None
            try: air_temp, air_humidity = sensors.test_dht()
            except Exception as e: print(f"[ERROR] DHT22: {e}"); air_temp, air_humidity = None, None
            try: soil_temp = sensors.read_ds18b20_temp()
            except Exception as e: print(f"[ERROR] DS18B20: {e}"); soil_temp = None

            # --- Upis u bazu ---
            stable_flag = 1
            database.insert_log(
                datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'),
                round(air_temp, 2) if air_temp is not None else None,
                round(air_humidity, 2) if air_humidity is not None else None,
                round(soil_temp, 2) if soil_temp is not None else None,
                soil_raw,
                round(soil_voltage, 3) if soil_voltage is not None else None,
                round(soil_percent, 2) if soil_percent is not None else None,
                round(lux, 2) if lux is not None else None,
                stable_flag
            )
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Zapis spremljen.")

            # Automatsko zalijevanje je privremeno isključeno
            # if should_water(soil_percent):
            #     perform_watering()

            time.sleep(LOG_INTERVAL_SECONDS)
    finally:
        cleanup()


if __name__ == "__main__":
    try:
        hardware.initialize()
        run_logger()
    except Exception as e:
        print(f"Dogodila se kritična greška u loggeru: {e}")
    finally:
        hardware.cleanup()
        cleanup()
        print("Logger proces potpuno ugašen.")