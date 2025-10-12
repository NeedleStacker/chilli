import sys
import fake_rpi

# Replace libraries with fake ones
sys.modules['RPi'] = fake_rpi.RPi
sys.modules['RPi.GPIO'] = fake_rpi.RPi.GPIO
sys.modules['smbus'] = fake_rpi.smbus

import argparse

# Project modules
import hardware
import sensors
import database
from relays import test_relays

def main():
    """
    Command-line interface for managing and testing the chili plant system.

    This script provides a set of commands to interact with the hardware sensors,
    relays, and the database directly from the command line. It handles parsing
    of arguments, initializes the necessary hardware, executes the requested
    command, and ensures a clean shutdown.
    """
    parser = argparse.ArgumentParser(
        description="Management and testing tool for the chili plant system.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    # Definition of all available commands
    parser.add_argument(
        "command",
        choices=[
            "test_ads", "test_dht", "test_ds18b20", "test_relays", "test_bh1750",
            "calibrate_ads", "get_sql", "delete_sql"
        ],
        help="""Command to execute:
  - test_ads: Tests the soil moisture sensor (ADS1115).
  - test_dht: Tests the air temp/humidity sensor (DHT22).
  - test_ds18b20: Tests the soil temperature sensor (DS18B20).
  - test_relays: Tests both relays.
  - test_bh1750: Tests the light sensor (BH1750).
  - calibrate_ads: Calibrates the moisture sensor.
  - get_sql: Fetches and prints all records from the database.
  - delete_sql: Deletes records from the database.
"""
    )

    # Optional arguments
    parser.add_argument("--dry", action="store_true", help="For calibrate_ads: sets the 'dry' reference value.")
    parser.add_argument("--wet", action="store_true", help="For calibrate_ads: sets the 'wet' reference value.")
    parser.add_argument("--all", action="store_true", help="For delete_sql: deletes ALL records from the 'logs' table.")
    parser.add_argument("--ids", type=str, help="For delete_sql: specifies IDs to delete (e.g., '1,2,5' or '3-10').")

    args = parser.parse_args()

    # Hardware initialization is required for most commands
    print("Initializing hardware...")
    hardware.initialize()
    print("-" * 20)

    try:
        # Execute the selected command
        if args.command == "test_ads":
            sensors.test_ads()
        elif args.command == "test_dht":
            temp, hum = sensors.test_dht()
            if temp is not None and hum is not None:
                print(f"DHT22: Temperature={temp:.2f}°C, Humidity={hum:.2f}%")
            else:
                print("DHT22: Failed to read.")
        elif args.command == "test_ds18b20":
            sensors.test_ds18b20()
        elif args.command == "test_bh1750":
            lux = sensors.read_bh1750_lux()
            if lux is not None:
                print(f"BH1750 Light: {lux:.2f} lx")
            else:
                print("BH1750: Failed to read.")
        elif args.command == "test_relays":
            test_relays()
        elif args.command == "calibrate_ads":
            sensors.calibrate_ads(dry=args.dry, wet=args.wet)
        elif args.command == "get_sql":
            database.get_sql_data()
        elif args.command == "delete_sql":
            # Confirmation for deleting all data
            if args.all:
                confirm = input("⚠️  Are you sure you want to delete ALL data from the database? (yes/no): ")
                if confirm.lower() != 'yes':
                    print("Cancelled.")
                    return

            database.delete_sql_data(ids=args.ids, delete_all=args.all)

    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        # Ensure resources are always released
        print("-" * 20)
        print("Cleaning up hardware resources...")
        hardware.cleanup()
        print("Done.")

if __name__ == "__main__":
    main()