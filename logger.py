import time
import datetime
import os
import glob
import argparse
import RPi.GPIO as GPIO

from relays import init_relays, test_relays, set_relay_state, RELAY1
from config import LOGS_DIR, DHT_SENSOR_TYPE, DHT_SENSOR_PIN, STATUS_FILE
from database import init_db, delete_sql_data, get_sql_data
from sensors import (
    test_dht, test_ads, test_ds18b20, calibrate_ads,
    read_ds18b20_temp, read_soil_raw_shared, read_soil_raw_fresh,
    read_soil_percent_from_voltage, read_bh1750_lux
)
# from camera import capture_image

# pragovi za automatsko zalijevanje
WATERING_THRESHOLD = 40.0      # %
WATERING_DURATION = 10         # sekundi
WATERING_COOLDOWN = 3600       # sekundi (1h)
LAST_WATERING_FILE = "last_watering.txt"

def cleanup_old_images(folder, months=3):
    now = time.time()
    cutoff = now - (months * 30 * 24 * 3600)
    for f in glob.glob(os.path.join(folder, "*.jpg")):
        if os.path.getmtime(f) < cutoff:
            os.remove(f)


def should_water(soil_percent):
    """Provjerava prag vlage i cooldown."""
    if soil_percent is None:
        return False

    if soil_percent >= WATERING_THRESHOLD:
        return False

    if os.path.exists(LAST_WATERING_FILE):
        try:
            with open(LAST_WATERING_FILE, "r") as f:
                last_ts = float(f.read().strip())
            if time.time() - last_ts < WATERING_COOLDOWN:
                print("[AUTO] Preskačem zalijevanje (cooldown).")
                return False
        except Exception:
            pass

    return True


def perform_watering():
    """Aktivira pumpu uz safety logiku."""
    print(f"[AUTO] Uključujem pumpu na {WATERING_DURATION}s ...")
    set_relay_state(RELAY1, True)
    time.sleep(WATERING_DURATION)
    set_relay_state(RELAY1, False)
    with open(LAST_WATERING_FILE, "w") as f:
        f.write(str(time.time()))
    print("[AUTO] Zalijevanje završeno.")


def run_logger(cold_first=False):
    """Glavna petlja logiranja senzora."""
    now = datetime.datetime.now().strftime("%d.%m.%Y. u %H:%M:%S")
    pid = os.getpid()

    with open(STATUS_FILE, "w") as f:
        f.write(f"{now} (PID: {pid})")
        f.flush()
        os.fsync(f.fileno())  # forsira upis na disk

    init_relays()
    conn = init_db()
    c = conn.cursor()
    os.makedirs(LOGS_DIR, exist_ok=True)

    try:
        while True:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

            # --- BH1750 ---
            lux = read_bh1750_lux()

            # --- Soil ---
            if cold_first:
                soil_raw, soil_voltage = read_soil_raw_fresh()
            else:
                soil_raw, soil_voltage = read_soil_raw_shared()
            soil_percent = read_soil_percent_from_voltage(soil_voltage)

            # --- DHT22 ---
            humidity, temperature = None, None
            try:
                import Adafruit_DHT
                humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR_TYPE, DHT_SENSOR_PIN)
            except Exception as e:
                print(f"[DHT22] Greška: {e}")

            # --- DS18B20 ---
            temp_ds18b20 = read_ds18b20_temp()

            # --- Zaokruživanja ---
            humidity = round(humidity, 3) if humidity is not None else None
            temperature = round(temperature, 3) if temperature is not None else None
            temp_ds18b20 = round(temp_ds18b20, 3) if temp_ds18b20 is not None else None
            soil_voltage = round(soil_voltage, 3) if soil_voltage is not None else None
            soil_percent = round(soil_percent, 3) if soil_percent is not None else None

            # flag stabilnosti
            stable_flag = 1

            c.execute("""
                INSERT INTO logs (timestamp, dht22_air_temp, dht22_humidity,
                                  ds18b20_soil_temp, soil_raw, soil_voltage,
                                  soil_percent, lux, stable)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                temperature,
                humidity,
                temp_ds18b20,
                soil_raw,
                soil_voltage,
                soil_percent,
                lux,
                stable_flag
            ))

            conn.commit()

            mode_tag = "COLD" if cold_first else "SHARED"
            print(f"[{timestamp}] ({mode_tag}) "
                  f"Temp zraka:{temperature}C, Vlaga:{humidity}%, "
                  f"Temp zemlje:{temp_ds18b20}C, Soil%:{soil_percent}%, "
                  f"Lux:{lux}, STABLE={stable_flag}")

            cleanup_old_images(LOGS_DIR, months=3)
            time.sleep(2400)  # svakih 2400 sec = 40 min

    except KeyboardInterrupt:
        print("Zaustavljeno od strane korisnika.")
    finally:
        GPIO.cleanup()
        conn.close()
        if os.path.exists(STATUS_FILE):
            os.remove(STATUS_FILE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=[
        "run_first", "test_ads", "test_dht", "test_ds18b20",
        "test_relays", "calibrate_ads", "get_sql_data", "delete_sql_data"
    ])
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--wet", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--ids", type=str)
    args = parser.parse_args()

    if args.mode == "run_first":
        run_logger(cold_first=True)
    elif args.mode == "test_ads":
        test_ads()
    elif args.mode == "test_dht":
        test_dht()
    elif args.mode == "test_ds18b20":
        test_ds18b20()
    elif args.mode == "test_relays":
        test_relays()
    elif args.mode == "get_sql_data":
        get_sql_data()
    elif args.mode == "calibrate_ads":
        calibrate_ads(dry=args.dry, wet=args.wet)
    elif args.mode == "delete_sql_data":
        delete_sql_data(ids=args.ids, delete_all=args.all)
