import os
import Adafruit_DHT

# --- File and Directory Paths ---
# Base directory of the application.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Path to the soil moisture sensor calibration file.
CALIB_FILE = os.path.join(BASE_DIR, "soil_calibration.json")
# Path to the SQLite database file.
DB_FILE = os.path.join(BASE_DIR, "sensors.db")
# Directory for storing log files.
LOGS_DIR = os.path.join(BASE_DIR, "logs")
# File to store the status of the logger process.
STATUS_FILE = os.path.join(BASE_DIR, "logger_status.txt")
# File to store the timestamp of the last watering event.
LAST_WATERING_FILE = os.path.join(BASE_DIR, "last_watering.txt")

# --- GPIO Pin Configuration (BCM numbering) ---
# GPIO pin for the water pump relay.
RELAY1 = 12
# GPIO pin for the light relay or other secondary relay.
RELAY2 = 16
# GPIO data pin for the DHT22 temperature and humidity sensor.
DHT_PIN = 27

# --- Sensor Types and Addresses ---
# Type of DHT sensor being used.
DHT_SENSOR = Adafruit_DHT.DHT22
# Base directory for 1-Wire devices (e.g., DS18B20 temperature sensor).
W1_BASE_DIR = '/sys/bus/w1/devices/'
# I2C address for the BH1750 light sensor.
BH1750_ADDR = 0x23

# --- Application Settings ---
# Interval in seconds for logging sensor data.
LOG_INTERVAL_SECONDS = 2400
# Soil moisture threshold (in percent) for automatic watering.
WATERING_THRESHOLD_PERCENT = 40.0
# Duration in seconds for each watering cycle.
WATERING_DURATION_SECONDS = 10
# Cooldown period in seconds after watering before another cycle can be triggered.
WATERING_COOLDOWN_SECONDS = 3600