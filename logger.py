import time
import datetime
import os
import glob
import argparse

# Project modules
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
    """Deletes old images from the log directory.

    Args:
        folder (str): The path to the directory containing the images.
        months (int): The age in months after which images will be deleted.
    """
    now = time.time()
    cutoff = now - (months * 30 * 24 * 3600)
    for f in glob.glob(os.path.join(folder, "*.jpg")):
        if os.path.getmtime(f) < cutoff:
            try:
                os.remove(f)
            except OSError as e:
                print(f"[WARN] Could not delete old image {f}: {e}")


def should_water(soil_percent):
    """Checks if automatic watering should be initiated.

    Watering is triggered if the soil moisture is below the threshold and
    the cooldown period since the last watering has passed.

    Args:
        soil_percent (float): The current soil moisture percentage.

    Returns:
        bool: True if watering should be performed, False otherwise.
    """
    if soil_percent is None:
        return False

    if soil_percent >= WATERING_THRESHOLD_PERCENT:
        return False

    if os.path.exists(LAST_WATERING_FILE):
        try:
            with open(LAST_WATERING_FILE, "r") as f:
                last_ts = float(f.read().strip())
            if time.time() - last_ts < WATERING_COOLDOWN_SECONDS:
                print("[AUTO] Skipping watering (cooldown period is active).")
                return False
        except (ValueError, IOError):
            # If the file is invalid, proceed as if it doesn't exist
            pass

    return True


def perform_watering():
    """Activates the water pump relay and records the event.

    This function turns on the pump for a configured duration, logs the
    event to the database, and updates the last watering timestamp file.
    It ensures the relay is turned off even if an error occurs.
    """
    print(f"[AUTO] Turning on the pump for {WATERING_DURATION_SECONDS} seconds...")
    try:
        set_relay_state(RELAY1, True)
        database.insert_relay_event("RELAY1", "ON", source="auto")
        time.sleep(WATERING_DURATION_SECONDS)
    finally:
        set_relay_state(RELAY1, False)
        database.insert_relay_event("RELAY1", "OFF", source="auto")

    try:
        with open(LAST_WATERING_FILE, "w") as f:
            f.write(str(time.time()))
    except IOError as e:
        print(f"[ERROR] Could not write last watering time: {e}")

    print("[AUTO] Watering complete.")


def run_logger():
    """The main loop for periodically reading sensors and logging data.

    This function initializes the database, creates a status file, and then
    enters an infinite loop to:
    1. Read data from all connected sensors.
    2. Log the data to the database.
    3. Check if automatic watering is needed and perform it.
    4. Clean up old log files.
    5. Wait for the configured interval before repeating.
    It also handles cleanup (removing the status file) on exit.
    """
    print("Logger is starting...")
    # Ensure the database and tables exist before the main loop
    database.init_db()
    os.makedirs(LOGS_DIR, exist_ok=True)

    # Write status that the logger is running
    try:
        with open(STATUS_FILE, "w") as f:
            f.write(f"RUNNING @ {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')} (PID: {os.getpid()})")
    except IOError as e:
        print(f"[ERROR] Could not write status file: {e}")

    try:
        while True:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Reading all sensors
            lux = sensors.read_bh1750_lux()
            soil_raw, soil_voltage = sensors.read_soil_raw()
            soil_percent = sensors.read_soil_percent_from_voltage(soil_voltage)
            air_temp, air_humidity = sensors.test_dht()
            soil_temp = sensors.read_ds18b20_temp()

            # Round values for data cleanliness
            air_humidity = round(air_humidity, 2) if air_humidity is not None else None
            air_temp = round(air_temp, 2) if air_temp is not None else None
            soil_temp = round(soil_temp, 2) if soil_temp is not None else None
            soil_voltage = round(soil_voltage, 3) if soil_voltage is not None else None
            soil_percent = round(soil_percent, 2) if soil_percent is not None else None
            lux = round(lux, 2) if lux is not None else None

            # Insert into database - the function now manages its own connection
            database.insert_log(timestamp, air_temp, air_humidity, soil_temp,
                                soil_raw, soil_voltage, soil_percent, lux)

            print(f"[{timestamp}] AirTemp:{air_temp}°C, AirHumidity:{air_humidity}%, "
                  f"SoilTemp:{soil_temp}°C, SoilMoisture:{soil_percent}%, "
                  f"Lux:{lux} lx")

            # Check and perform automatic watering
            if should_water(soil_percent):
                perform_watering()

            cleanup_old_images(LOGS_DIR, months=3)
            time.sleep(LOG_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        # Remove the status file on shutdown
        if os.path.exists(STATUS_FILE):
            os.remove(STATUS_FILE)
        print("Logger stopped.")


# The logger.py file is now a clean module.
# To run the logger, use `webserver.py`.
# For testing and administration, use `manage.py`.