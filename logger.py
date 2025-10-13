import time
import datetime
import os
import glob
import argparse
import RPi.GPIO as GPIO
import logging
from typing import Optional

from relays import initialize_relays, run_relay_test_sequence, set_relay_state, RELAY1_PIN
from config import LOGS_DIR, STATUS_FILE
from database import initialize_database, delete_logs, get_all_logs
from sensors import (
    read_dht22_sensor,
    test_ads1115_sensor,
    test_dht22_sensor,
    test_ds18b20_sensor,
    calibrate_soil_moisture_sensor,
    read_ds18b20_temperature,
    read_soil_moisture_raw,
    convert_voltage_to_soil_percentage,
    read_bh1750_light_intensity,
)

# --- Constants for Automated Watering ---
WATERING_THRESHOLD_PERCENT = 40.0
WATERING_DURATION_SECONDS = 10
WATERING_COOLDOWN_SECONDS = 3600  # 1 hour
LAST_WATERING_TIMESTAMP_FILE = "last_watering.txt"

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def cleanup_old_log_images(folder: str, months: int = 3) -> None:
    """Removes JPG files older than a specified number of months from a folder."""
    now = time.time()
    cutoff = now - (months * 30 * 24 * 3600)
    for filepath in glob.glob(os.path.join(folder, "*.jpg")):
        try:
            if os.path.getmtime(filepath) < cutoff:
                os.remove(filepath)
                logging.info(f"Removed old image: {filepath}")
        except OSError as e:
            logging.error(f"Error removing file {filepath}: {e}")

def should_initiate_watering(soil_moisture_percent: Optional[float]) -> bool:
    """
    Checks if the soil moisture is below the threshold and if the cooldown period has passed.
    """
    if soil_moisture_percent is None or soil_moisture_percent >= WATERING_THRESHOLD_PERCENT:
        return False

    if os.path.exists(LAST_WATERING_TIMESTAMP_FILE):
        try:
            with open(LAST_WATERING_TIMESTAMP_FILE, "r") as f:
                last_timestamp = float(f.read().strip())
            if time.time() - last_timestamp < WATERING_COOLDOWN_SECONDS:
                logging.info("Skipping watering due to cooldown period.")
                return False
        except (ValueError, IOError):
            pass  # Ignore if file is corrupted or unreadable

    return True

def perform_watering_cycle() -> None:
    """Activates the water pump for a predefined duration and logs the event."""
    logging.info(f"Starting pump for {WATERING_DURATION_SECONDS} seconds...")
    set_relay_state(RELAY1_PIN, True)
    time.sleep(WATERING_DURATION_SECONDS)
    set_relay_state(RELAY1_PIN, False)
    try:
        with open(LAST_WATERING_TIMESTAMP_FILE, "w") as f:
            f.write(str(time.time()))
    except IOError as e:
        logging.error(f"Could not write to watering timestamp file: {e}")
    logging.info("Watering cycle complete.")

def run_logging_cycle(use_shared_i2c: bool = False) -> None:
    """
    Main loop for logging sensor data to the database.
    """
    current_time_str = datetime.datetime.now().strftime("%d.%m.%Y. at %H:%M:%S")
    pid = os.getpid()

    try:
        with open(STATUS_FILE, "w") as f:
            f.write(f"RUNNING since {current_time_str} (PID: {pid})")
            f.flush()
    except IOError as e:
        logging.error(f"Could not write to status file: {e}")

    initialize_relays()
    db_connection = initialize_database()
    cursor = db_connection.cursor()
    os.makedirs(LOGS_DIR, exist_ok=True)

    try:
        while True:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

            # --- Read all sensors ---
            lux = read_bh1750_light_intensity()
            soil_raw, soil_voltage = read_soil_moisture_raw(use_shared_i2c=use_shared_i2c)
            soil_percent = convert_voltage_to_soil_percentage(soil_voltage)
            temperature, humidity = read_dht22_sensor()
            soil_temperature = read_ds18b20_temperature()

            # --- Round values ---
            humidity = round(humidity, 3) if humidity is not None else None
            temperature = round(temperature, 3) if temperature is not None else None
            soil_temperature = round(soil_temperature, 3) if soil_temperature is not None else None
            soil_voltage = round(soil_voltage, 3) if soil_voltage is not None else None
            soil_percent = round(soil_percent, 3) if soil_percent is not None else None

            if should_initiate_watering(soil_percent):
                perform_watering_cycle()

            # --- Insert data ---
            stability_flag = 1
            cursor.execute("""
                INSERT INTO logs (timestamp, dht22_air_temp, dht22_humidity,
                                  ds18b20_soil_temp, soil_raw, soil_voltage,
                                  soil_percent, lux, stable)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, temperature, humidity, soil_temperature,
                soil_raw, soil_voltage, soil_percent, lux, stability_flag,
            ))
            db_connection.commit()

            readout_mode = "SHARED_I2C" if use_shared_i2c else "FRESH_I2C"
            logging.info(
                f"({readout_mode}) Air Temp: {temperature}°C, Humidity: {humidity}%, "
                f"Soil Temp: {soil_temperature}°C, Soil Moisture: {soil_percent}%, "
                f"Light: {lux} Lux"
            )

            cleanup_old_log_images(LOGS_DIR, months=3)
            time.sleep(2400)

    except KeyboardInterrupt:
        logging.info("Logger stopped by user.")
    finally:
        GPIO.cleanup()
        db_connection.close()
        if os.path.exists(STATUS_FILE):
            os.remove(STATUS_FILE)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chilli Plant Monitoring and Automation Logger")
    parser.add_argument(
        "mode",
        choices=[
            "run", "run_first", "run_shared_i2c", "test_ads1115", "test_dht22",
            "test_ds18b20", "test_relays", "calibrate_soil_moisture",
            "get_all_logs", "delete_logs",
        ],
        help="The operation mode.",
    )
    parser.add_argument("--dry", action="store_true", help="Set the dry calibration point.")
    parser.add_argument("--wet", action="store_true", help="Set the wet calibration point.")
    parser.add_argument("--all", action="store_true", help="Delete all log records.")
    parser.add_argument("--ids", type=str, help="Comma-separated IDs or ranges to delete (e.g., '1,3,5-10').")
    args = parser.parse_args()

    if args.mode == "run":
        run_logging_cycle(use_shared_i2c=False)
    elif args.mode == "run_first":
        run_logging_cycle(use_shared_i2c=False)
    elif args.mode == "run_shared_i2c":
        run_logging_cycle(use_shared_i2c=True)
    elif args.mode == "test_ads1115":
        test_ads1115_sensor()
    elif args.mode == "test_dht22":
        test_dht22_sensor()
    elif args.mode == "test_ds18b20":
        test_ds18b20_sensor()
    elif args.mode == "test_relays":
        run_relay_test_sequence()
    elif args.mode == "get_all_logs":
        get_all_logs()
    elif args.mode == "calibrate_soil_moisture":
        calibrate_soil_moisture_sensor(dry=args.dry, wet=args.wet)
    elif args.mode == "delete_logs":
        delete_logs(ids=args.ids, delete_all=args.all)
