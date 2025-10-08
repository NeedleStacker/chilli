import time
import datetime
import os
import glob
import argparse

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

def cleanup_old_images(folder, months=3):
    """Briše stare slike iz log direktorija."""
    now = time.time()
    cutoff = now - (months * 30 * 24 * 3600)
    for f in glob.glob(os.path.join(folder, "*.jpg")):
        if os.path.getmtime(f) < cutoff:
            try:
                os.remove(f)
            except OSError as e:
                print(f"[WARN] Nije moguće obrisati staru sliku {f}: {e}")


def should_water(soil_percent):
    """Provjerava treba li pokrenuti automatsko zalijevanje."""
    if soil_percent is None:
        return False

    if soil_percent >= WATERING_THRESHOLD_PERCENT:
        return False

    if os.path.exists(LAST_WATERING_FILE):
        try:
            with open(LAST_WATERING_FILE, "r") as f:
                last_ts = float(f.read().strip())
            if time.time() - last_ts < WATERING_COOLDOWN_SECONDS:
                print("[AUTO] Preskačem zalijevanje (cooldown period je aktivan).")
                return False
        except (ValueError, IOError):
            pass

    return True


def perform_watering():
    """Aktivira relej pumpe za vodu i bilježi vrijeme."""
    print(f"[AUTO] Uključujem pumpu na {WATERING_DURATION_SECONDS} sekundi...")
    try:
        set_relay_state(RELAY1, True)
        time.sleep(WATERING_DURATION_SECONDS)
        database.insert_relay_event("RELAY1", "ON", source="auto")
    finally:
        set_relay_state(RELAY1, False)
        database.insert_relay_event("RELAY1", "OFF", source="auto")

    try:
        with open(LAST_WATERING_FILE, "w") as f:
            f.write(str(time.time()))
    except IOError as e:
        print(f"[ERROR] Nije moguće zapisati vrijeme zadnjeg zalijevanja: {e}")

    print("[AUTO] Zalijevanje završeno.")


def run_logger():
    """Glavna petlja za periodično očitavanje senzora i upis u bazu."""
    print("Logger se pokreće...")
    # Osiguraj da baza i tablice postoje prije glavne petlje
    database.init_db()
    os.makedirs(LOGS_DIR, exist_ok=True)

    # Zapiši status da je logger pokrenut
    try:
        with open(STATUS_FILE, "w") as f:
            f.write(f"RUNNING @ {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')} (PID: {os.getpid()})")
    except IOError as e:
        print(f"[ERROR] Nije moguće zapisati statusnu datoteku: {e}")

    try:
        while True:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Očitavanje svih senzora
            lux = sensors.read_bh1750_lux()
            soil_raw, soil_voltage = sensors.read_soil_raw()
            soil_percent = sensors.read_soil_percent_from_voltage(soil_voltage)
            air_temp, air_humidity = sensors.test_dht()
            soil_temp = sensors.read_ds18b20_temp()

            # Zaokruživanje vrijednosti radi čistoće podataka
            air_humidity = round(air_humidity, 2) if air_humidity is not None else None
            air_temp = round(air_temp, 2) if air_temp is not None else None
            soil_temp = round(soil_temp, 2) if soil_temp is not None else None
            soil_voltage = round(soil_voltage, 3) if soil_voltage is not None else None
            soil_percent = round(soil_percent, 2) if soil_percent is not None else None
            lux = round(lux, 2) if lux is not None else None

            # Upis u bazu - funkcija sada sama upravlja konekcijom
            database.insert_log(timestamp, air_temp, air_humidity, soil_temp,
                                soil_raw, soil_voltage, soil_percent, lux)

            print(f"[{timestamp}] TempZrak:{air_temp}°C, VlagaZrak:{air_humidity}%, "
                  f"TempZemlja:{soil_temp}°C, VlagaZemlja:{soil_percent}%, "
                  f"Lux:{lux} lx")

            # Provjera i izvršavanje automatskog zalijevanja
            if should_water(soil_percent):
                perform_watering()

            cleanup_old_images(LOGS_DIR, months=3)
            time.sleep(LOG_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nZaustavljeno od strane korisnika.")
    finally:
        # Ukloni statusnu datoteku pri gašenju
        if os.path.exists(STATUS_FILE):
            os.remove(STATUS_FILE)
        print("Logger zaustavljen.")


# Datoteka logger.py je sada čisti modul.
# Za pokretanje loggera, koristite `webserver.py`.
# Za testiranje i administraciju, koristite `manage.py`.