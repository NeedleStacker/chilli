import os
import glob
import Adafruit_DHT
import RPi.GPIO as GPIO

# --- I2C Initialization ---
# This I2C bus is shared across sensor modules to avoid re-initialization.
try:
    import board
    import busio
    i2c = busio.I2C(board.SCL, board.SDA)
except (NotImplementedError, NameError, AttributeError):
    print("Warning: Could not initialize I2C bus. This is expected on non-Raspberry Pi systems.")
    i2c = None


# --- GPIO Setup ---
GPIO.setmode(GPIO.BCM)

# --- Relej Setup ---
RELAY1_PIN = 12  # IN1
RELAY2_PIN = 16  # IN2
GPIO.setup(RELAY1_PIN, GPIO.OUT, initial=GPIO.HIGH)  # OFF by default (LOW-trigger)
GPIO.setup(RELAY2_PIN, GPIO.OUT, initial=GPIO.HIGH)

# --- DHT22 Setup ---
DHT_SENSOR_TYPE = Adafruit_DHT.DHT22
DHT_SENSOR_PIN = 27

# --- DS18B20 Setup ---
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
base_dir = '/sys/bus/w1/devices/'
try:
    device_folder = glob.glob(base_dir + '28-*')[0]
    DS18B20_DEVICE_FILE = device_folder + '/w1_slave'
except IndexError:
    print("Warning: DS18B20 sensor not found. Please check the connection.")
    DS18B20_DEVICE_FILE = None


# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CALIBRATION_FILE = os.path.join(BASE_DIR, "soil_calibration.json")
DATABASE_FILE = os.path.join(BASE_DIR, "sensors.db")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
STATUS_FILE = os.path.join(BASE_DIR, "logger_status.txt")
