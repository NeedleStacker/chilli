import time
import datetime
import os
import sys
import signal
import atexit

# Moduli projekta
import hardware
import database
import sensors
from relays import set_relay_state
from config import (
    LOGS_DIR, STATUS_FILE, LAST_WATERING_FILE, PID_FILE,
    LOG_INTERVAL_SECONDS, WATERING_THRESHOLD_PERCENT,
    WATERING_DURATION_SECONDS, WATERING_COOLDOWN_SECONDS,
    RELAY1
)

def cleanup():
    """Funkcija za čišćenje koja se poziva pri izlasku iz programa."""
    print("Čistim PID i status datoteke...")
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    if os.path.exists(STATUS_FILE):
        os.remove(STATUS_FILE)

def handle_signal(signum, frame):
    """Handler za signale (npr. SIGTERM) za sigurno gašenje."""
    print(f"Primljen signal {signum}, gasim se...")
    sys.exit(0)

# Registriraj handlere
atexit.register(cleanup)
signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

def check_if_already_running():
    """Provjerava postoji li već aktivan logger proces."""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            # Provjeri postoji li proces s tim PID-om
            os.kill(pid, 0)
            print(f"Logger proces s PID-om {pid} je već aktivan. Izlazim.")
            return True # Proces je aktivan
        except (OSError, ValueError):
            # Proces ne postoji ili je PID datoteka neispravna, brišemo je
            print("Pronađena stara/neispravna PID datoteka, brišem je.")
            os.remove(PID_FILE)
    return False

def run_logger():
    """Glavna petlja za periodično očitavanje senzora i upis u bazu."""
    pid = os.getpid()
    with open(PID_FILE, "w") as f:
        f.write(str(pid))

    print(f"Logger se pokreće s PID: {pid}...")
    database.init_db()
    os.makedirs(LOGS_DIR, exist_ok=True)

    while True:
        with open(STATUS_FILE, "w") as f:
            f.write(f"RUNNING @ {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')} (PID: {pid})")

        # Očitavanje senzora s novom, otpornijom logikom iz sensors.py
        lux = sensors.read_bh1750_lux()
        soil_raw, soil_voltage = sensors.read_soil_raw()
        air_temp, air_humidity = sensors.test_dht()
        soil_temp = sensors.read_ds18b20_temp()

        # Izračunaj postotak vlažnosti samo ako je očitavanje napona uspjelo
        if soil_voltage is not None:
            soil_percent = sensors.read_soil_percent_from_voltage(soil_voltage)
        else:
            soil_percent = None

        # Provjera jesu li sva očitanja uspjela
        stable_flag = 1 if all(v is not None for v in [lux, soil_voltage, air_temp, soil_temp]) else 0
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


if __name__ == "__main__":
    if check_if_already_running():
        sys.exit(1)

    try:
        hardware.initialize()
        run_logger()
    except Exception as e:
        print(f"Dogodila se kritična greška u loggeru: {e}")
    finally:
        hardware.cleanup()
        print("Logger proces potpuno ugašen.")