import os
import Adafruit_DHT

# --- Putevi (Paths) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CALIB_FILE = os.path.join(BASE_DIR, "soil_calibration.json")
DB_FILE = os.path.join(BASE_DIR, "sensors.db")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
STATUS_FILE = os.path.join(BASE_DIR, "logger_status.txt")
LAST_WATERING_FILE = os.path.join(BASE_DIR, "last_watering.txt")

# --- GPIO Pinovi (BCM numeriranje) ---
RELAY1 = 12  # IN1 pin za relej pumpe
RELAY2 = 16  # IN2 pin za relej svjetla (ili drugi)
DHT_PIN = 27 # Data pin za DHT22 senzor

# --- Senzori - Tipovi i adrese ---
DHT_SENSOR = Adafruit_DHT.DHT22
W1_BASE_DIR = '/sys/bus/w1/devices/' # Bazni direktorij za 1-Wire uređaje
BH1750_ADDR = 0x23 # I2C adresa za BH1750 (ili 0x5C)

# --- Postavke Aplikacije ---
LOG_INTERVAL_SECONDS = 2400 # Interval logiranja (40 minuta)
WATERING_THRESHOLD_PERCENT = 40.0 # Prag vlažnosti za automatsko zalijevanje
WATERING_DURATION_SECONDS = 10 # Trajanje zalijevanja u sekundama
WATERING_COOLDOWN_SECONDS = 3600 # Vrijeme mirovanja nakon zalijevanja (1 sat)