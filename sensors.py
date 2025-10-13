import os
import json
import time
import glob
import smbus2
import Adafruit_DHT

# Project modules
import hardware  # To access the initialized hardware.i2c
from config import (
    CALIB_FILE, W1_BASE_DIR, BH1750_ADDR,
    DHT_SENSOR, DHT_PIN
)

# Adafruit libraries for ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_ads1x15.ads1115 as ADS


# --- Private helper function for ADS1115 ---
def _read_ads_once(ads_instance):
    """
    Performs a single, stable reading from the ADS1115.

    This includes a "flush" step by taking a dummy reading first to
    stabilize the ADC value.

    Args:
        ads_instance: An initialized ADS1115 object.

    Returns:
        A tuple containing the raw ADC value (int) and the voltage (float).
    """
    chan = AnalogIn(ads_instance, ADS.P0)
    _ = chan.value  # First reading to "wake up" the channel
    time.sleep(0.05)
    raw = chan.value
    voltage = chan.voltage
    return raw, voltage


# --- Main Sensor Reading Functions ---

def read_soil_raw():
    """
    Reads the raw value and voltage from the ADS1115 soil moisture sensor.

    Uses the global I2C bus initialized in 'hardware.py'.

    Returns:
        A tuple (raw_value, voltage) or (None, None) if the reading fails.
    """
    if hardware.i2c is None:
        print("[ERROR] I2C bus not initialized. Cannot read moisture sensor.")
        return None, None
    try:
        ads = ADS.ADS1115(hardware.i2c)
        ads.gain = 1
        return _read_ads_once(ads)
    except Exception as e:
        print(f"[ERROR] Error reading from ADS1115: {e}")
        return None, None


def _get_ds18b20_device_file():
    """
    Finds the 1-Wire device file for the DS18B20 sensor.

    Returns:
        The path to the device file as a string, or None if not found.
    """
    try:
        # Search for a directory starting with '28-'
        device_folders = glob.glob(os.path.join(W1_BASE_DIR, '28-*'))
        if not device_folders:
            print("[WARN] DS18B20 sensor not found (no '28-*' directory).")
            return None
        # Return the full path to the 'w1_slave' file
        return os.path.join(device_folders[0], 'w1_slave')
    except Exception as e:
        print(f"[ERROR] Error finding DS18B20 device: {e}")
        return None


def read_ds18b20_temp():
    """
    Reads the temperature from a DS18B20 sensor.

    Returns:
        The temperature in degrees Celsius (float), or None on failure.
    """
    device_file = _get_ds18b20_device_file()
    if not device_file:
        return None

    try:
        with open(device_file, 'r') as f:
            lines = f.readlines()

        # Check the CRC (cyclic redundancy check)
        if lines[0].strip()[-3:] != 'YES':
            print("[WARN] DS18B20 CRC check failed.")
            return None

        # Find the temperature in the second line
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp_string = lines[1][equals_pos + 2:]
            return float(temp_string) / 1000.0
    except (IOError, IndexError, ValueError) as e:
        print(f"[ERROR] Error reading temperature from DS18B20: {e}")
        return None


def read_bh1750_lux():
    """
    Reads the ambient light level in Lux from a BH1750 sensor.

    Returns:
        The light level in Lux (float), or None on failure.
    """
    try:
        # Continuous high-resolution mode
        BH1750_MODE = 0x10
        bus = smbus2.SMBus(1)  # Use /dev/i2c-1
        bus.write_byte(BH1750_ADDR, BH1750_MODE)
        time.sleep(0.2) # Wait for the sensor to take a measurement
        data = bus.read_i2c_block_data(BH1750_ADDR, 0, 2)
        lux = (data[0] << 8 | data[1]) / 1.2
        bus.close()
        return lux
    except Exception as e:
        print(f"[WARN] BH1750 reading failed: {e}")
        return None


def test_dht():
    """
    Reads from the DHT22 sensor.

    Returns:
        A tuple (temperature, humidity) or (None, None) on failure.
    """
    try:
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        return temperature, humidity
    except Exception as e:
        print(f"[WARN] DHT22 reading failed: {e}")
        return None, None


# --- Calibration and Percentage Calculation ---

def load_calibration():
    """
    Loads calibration values (dry/wet) from the JSON file.

    Returns:
        A dictionary with "dry_v" and "wet_v" keys. Returns default values
        if the file is not found or is invalid.
    """
    defaults = {"dry_v": 1.60, "wet_v": 0.20}
    if not os.path.exists(CALIB_FILE):
        print("[WARN] Calibration file not found, using default values.")
        return defaults
    try:
        with open(CALIB_FILE, "r") as f:
            calib = json.load(f)
        # Ensure the correct keys exist
        if "dry_v" in calib and "wet_v" in calib:
            return {"dry_v": float(calib["dry_v"]), "wet_v": float(calib["wet_v"])}
        else:
            print("[WARN] Keys 'dry_v' and 'wet_v' not found, using default values.")
            return defaults
    except (json.JSONDecodeError, TypeError) as e:
        print(f"[ERROR] Error reading calibration file: {e}. Using default values.")
        return defaults


def read_soil_percent_from_voltage(voltage, debug=False):
    """
    Converts sensor voltage to a moisture percentage (0-100%).

    Args:
        voltage (float): The voltage from the soil moisture sensor.
        debug (bool): If True, prints debugging information.

    Returns:
        The calculated moisture percentage (float), clamped between 0.0 and 100.0.
    """
    if voltage is None:
        return 0.0

    calib = load_calibration()
    dry_v, wet_v = calib["dry_v"], calib["wet_v"]

    # Ensure dry_v is always the higher value
    if dry_v < wet_v:
        dry_v, wet_v = wet_v, dry_v

    span = dry_v - wet_v
    if span <= 0:
        return 0.0

    # Calculate percentage
    percent = 100 * (dry_v - voltage) / span
    percent = max(0.0, min(100.0, percent)) # Clamp to 0-100

    if debug:
        print(f"[DEBUG] V={voltage:.3f}V, Dry={dry_v}V, Wet={wet_v}V -> {percent:.2f}%")

    return percent


# --- Command-line Test Functions ---

def test_ds18b20():
    """Tests the DS18B20 sensor and prints the result."""
    temp = read_ds18b20_temp()
    if temp is not None:
        print(f"DS18B20 Temperature: {temp:.2f}°C")
    else:
        print("DS18B20: Failed to read.")


def test_ads():
    """Tests the ADS1115 sensor and prints the result."""
    raw, voltage = read_soil_raw()
    if raw is not None:
        pct = read_soil_percent_from_voltage(voltage, debug=True)
        print(f"ADS1115: Raw={raw}, Voltage={voltage:.3f}V")
        print(f"Calculated moisture: {pct:.2f}%")
    else:
        print("ADS1115: Failed to read.")


def calibrate_ads(dry=False, wet=False):
    """Saves calibration values for the soil moisture sensor.

    Args:
        dry (bool): If True, save the current reading as the 'dry' reference.
        wet (bool): If True, save the current reading as the 'wet' reference.
    """
    if not dry and not wet:
        print("No option selected. Use --dry or --wet.")
        return

    raw, voltage = read_soil_raw()
    if voltage is None:
        print("[ERROR] Cannot read ADS1115 for calibration.")
        return

    calib = load_calibration()
    if dry:
        calib["dry_v"] = voltage
        print(f"Saved 'DRY' reference: {voltage:.3f}V")
    if wet:
        calib["wet_v"] = voltage
        print(f"Saved 'WET' reference: {voltage:.3f}V")

    try:
        with open(CALIB_FILE, "w") as f:
            json.dump(calib, f, indent=4)
        print("Calibration saved successfully.")
    except IOError as e:
        print(f"[ERROR] Could not save calibration file: {e}")