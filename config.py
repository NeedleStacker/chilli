import os
import Adafruit_DHT

# --- Putevi (Paths) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CALIB_FILE = os.path.join(BASE_DIR, "soil_calibration.json")
DB_FILE = os.path.join(BASE_DIR, "sensors.db")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
STATUS_FILE = os.path.join(BASE_DIR, "logger_status.txt")
PID_FILE = os.path.join(BASE_DIR, "logger.pid")
LAST_WATERING_FILE = os.path.join(BASE_DIR, "last_watering.txt")

# --- GPIO Pinovi (BCM numeriranje) ---
RELAY1 = 12
RELAY2 = 16
DHT_PIN = 27

# --- Senzori - Tipovi i adrese ---
DHT_SENSOR = Adafruit_DHT.DHT22
W1_BASE_DIR = '/sys/bus/w1/devices/'
BH1750_ADDR = 0x23

# --- Postavke Aplikacije ---
DEV_MODE = True # Ako je True, senzori vraćaju lažne podatke. Postaviti na False za produkciju.
LOG_INTERVAL_SECONDS = 2400 # Vraćeno na 40 minuta
WATERING_THRESHOLD_PERCENT = 40.0
WATERING_DURATION_SECONDS = 5
WATERING_COOLDOWN_SECONDS = 60