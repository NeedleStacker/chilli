import os
import json
import time
import datetime
import smbus2
from typing import Tuple, Optional, Dict, Any

import board
import busio
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_ads1x15.ads1115 as ADS

from config import (
    CALIBRATION_FILE,
    DS18B20_DEVICE_FILE,
    DHT_SENSOR_TYPE,
    DHT_SENSOR_PIN,
    i2c as shared_i2c,
)

# --- Constants ---
BH1750_I2C_ADDRESS = 0x23  # Use 0x5C if ADDR pin is high
BH1750_CONTINUOUS_HIGH_RES_MODE = 0x10

# --- ADS1115 Soil Moisture Sensor ---

def _read_ads1115_stable(ads: ADS.ADS1115) -> Tuple[int, float]:
    """
    Performs a stable read from the ADS1115 ADC.

    This includes a "flush" read to ensure the subsequent value is current.

    Args:
        ads (ADS.ADS1115): The ADS1115 object.

    Returns:
        Tuple[int, float]: The raw ADC value and the corresponding voltage.
    """
    channel = AnalogIn(ads, ADS.P0)
    _ = channel.value  # First read to flush
    time.sleep(0.05)
    raw_value = channel.value
    voltage = channel.voltage
    return raw_value, voltage

def read_soil_moisture_raw(use_shared_i2c: bool = False) -> Tuple[Optional[int], Optional[float]]:
    """
    Reads the raw soil moisture value and voltage from the ADS1115 sensor.

    To prevent unstable readings observed with a shared I2C bus, this function
    creates a new I2C object by default for each call.

    Args:
        use_shared_i2c (bool): If True, uses the shared I2C bus from config.

    Returns:
        Tuple[Optional[int], Optional[float]]: Raw ADC value and voltage, or (None, None) on failure.
    """
    try:
        i2c = shared_i2c if use_shared_i2c else busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c)
        ads.gain = 1
        raw, voltage = _read_ads1115_stable(ads)
        if not use_shared_i2c:
            del ads
            del i2c
        return raw, voltage
    except Exception as e:
        print(f"[Warning] Failed to read from ADS1115: {e}")
        return None, None

def convert_voltage_to_soil_percentage(voltage: Optional[float], debug: bool = False) -> float:
    """
    Converts soil moisture sensor voltage to a percentage based on calibration values.

    Args:
        voltage (Optional[float]): The voltage to convert.
        debug (bool): If True, prints debugging information.

    Returns:
        float: The calculated soil moisture percentage (0-100).
    """
    calibration = load_voltage_calibration()
    dry_voltage = float(calibration["dry_v"])
    wet_voltage = float(calibration["wet_v"])

    # Ensure dry_voltage is always greater than wet_voltage
    if dry_voltage < wet_voltage:
        dry_voltage, wet_voltage = wet_voltage, dry_voltage

    voltage_range = dry_voltage - wet_voltage
    if voltage_range <= 0:
        if debug:
            print(f"[Debug] Invalid calibration range: dry_v={dry_voltage}, wet_v={wet_voltage}")
        return 0.0

    if voltage is None:
        return 0.0

    # Calculate percentage (inverted scale)
    if voltage >= dry_voltage:
        percent = 0.0
    elif voltage <= wet_voltage:
        percent = 100.0
    else:
        percent = (dry_voltage - voltage) * 100.0 / voltage_range

    # Clamp the value between 0 and 100
    percent = max(0.0, min(100.0, percent))

    if debug:
        print(
            f"[Debug] voltage={voltage:.4f}, dry_v={dry_voltage:.4f}, "
            f"wet_v={wet_voltage:.4f}, range={voltage_range:.4f}, percent={percent:.3f}"
        )
    return round(percent, 3)

def read_soil_moisture_percentage(
    voltage: Optional[float] = None, use_shared_i2c: bool = False, debug: bool = False
) -> float:
    """
    A wrapper to get the soil moisture percentage.

    If voltage is not provided, it will be read from the sensor first.

    Args:
        voltage (Optional[float]): The sensor voltage.
        use_shared_i2c (bool): Passed to the raw reading function.
        debug (bool): Passed to the conversion function.

    Returns:
        float: The soil moisture percentage.
    """
    if voltage is None:
        _, voltage = read_soil_moisture_raw(use_shared_i2c=use_shared_i2c)
    return convert_voltage_to_soil_percentage(voltage, debug=debug)


# --- DS18B20 Soil Temperature Sensor ---

def read_ds18b20_temperature() -> Optional[float]:
    """
    Reads the soil temperature from the DS18B20 sensor.

    Returns:
        Optional[float]: The temperature in Celsius, or None if the read fails.
    """
    if not DS18B20_DEVICE_FILE or not os.path.exists(DS18B20_DEVICE_FILE):
        return None
    try:
        with open(DS18B20_DEVICE_FILE, 'r') as f:
            lines = f.readlines()
        if lines[0].strip()[-3:] != 'YES':
            return None
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp_string = lines[1][equals_pos + 2 :]
            return float(temp_string) / 1000.0
    except (IOError, IndexError, ValueError) as e:
        print(f"[Warning] Failed to read DS18B20 sensor: {e}")
        return None
    return None


# --- BH1750 Light Sensor ---

def read_bh1750_light_intensity() -> Optional[float]:
    """
    Reads the ambient light intensity in Lux from the BH1750 sensor.

    Returns:
        Optional[float]: The light intensity in Lux, or None on failure.
    """
    try:
        bus = smbus2.SMBus(1)  # I2C bus 1
        bus.write_byte(BH1750_I2C_ADDRESS, BH1750_CONTINUOUS_HIGH_RES_MODE)
        time.sleep(0.2)
        data = bus.read_i2c_block_data(BH1750_I2C_ADDRESS, 0, 2)
        lux = (data[0] << 8 | data[1]) / 1.2
        bus.close()
        return round(lux, 2)
    except Exception as e:
        print(f"[Warning] Failed to read from BH1750: {e}")
        return None


# --- DHT22 Air Temperature & Humidity Sensor ---

def read_dht22_sensor() -> Tuple[Optional[float], Optional[float]]:
    """
    Reads temperature and humidity from the DHT22 sensor.

    Returns:
        Tuple[Optional[float], Optional[float]]: Temperature (C) and humidity (%), or (None, None).
    """
    try:
        import Adafruit_DHT
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR_TYPE, DHT_SENSOR_PIN)
        return temperature, humidity
    except Exception as e:
        print(f"[Warning] Failed to read DHT22 sensor: {e}")
        return None, None


# --- Calibration ---

def load_voltage_calibration() -> Dict[str, float]:
    """
    Loads voltage calibration data from the JSON file.

    Expects format: {"dry_v": 1.60, "wet_v": 0.20}
    Falls back to default values if the file is missing or invalid.

    Returns:
        Dict[str, float]: A dictionary with 'dry_v' and 'wet_v' keys.
    """
    default_dry_v = 1.60
    default_wet_v = 0.20
    defaults = {"dry_v": default_dry_v, "wet_v": default_wet_v}

    if not os.path.exists(CALIBRATION_FILE):
        print("[Warning] Calibration file not found. Using default values.")
        return defaults

    try:
        with open(CALIBRATION_FILE, "r") as f:
            data = json.load(f)
        if "dry_v" in data and "wet_v" in data:
            return {"dry_v": float(data["dry_v"]), "wet_v": float(data["wet_v"])}
        if "dry" in data and "wet" in data:  # Legacy format support
            print("[Warning] Found old RAW calibration format. Using default voltage limits.")
        return defaults
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        print(f"[Error] Failed to read calibration file: {e}. Using default values.")
        return defaults

def calibrate_soil_moisture_sensor(dry: bool = False, wet: bool = False) -> None:
    """
    Saves new calibration values for the soil moisture sensor.

    Args:
        dry (bool): If True, sets the current reading as the dry reference.
        wet (bool): If True, sets the current reading as the wet reference.
    """
    _, voltage = read_soil_moisture_raw()
    if voltage is None:
        print("[Error] Could not read from ADS1115 sensor for calibration.")
        return

    calibration = load_voltage_calibration()
    if dry:
        calibration["dry_v"] = float(voltage)
        print(f"New DRY reference saved: {voltage:.3f} V")
    if wet:
        calibration["wet_v"] = float(voltage)
        print(f"New WET reference saved: {voltage:.3f} V")

    with open(CALIBRATION_FILE, "w") as f:
        json.dump(calibration, f, indent=4)
    print("Calibration saved:", calibration)


# --- Sensor Test Functions ---

def test_dht22_sensor() -> None:
    """Tests the DHT22 sensor and prints the readings."""
    temperature, humidity = read_dht22_sensor()
    print(f"DHT22 Sensor: Temperature={temperature}°C, Humidity={humidity}%")

def test_ds18b20_sensor() -> None:
    """Tests the DS18B20 sensor and prints the reading."""
    temperature = read_ds18b20_temperature()
    print(f"DS18B20 Sensor: Soil Temperature={temperature}°C")

def test_ads1115_sensor() -> None:
    """Tests the ADS1115 sensor and prints the readings."""
    raw, voltage = read_soil_moisture_raw()
    percent = convert_voltage_to_soil_percentage(voltage, debug=True)
    print(
        f"ADS1115 Sensor: raw={raw}, voltage={voltage or 0.0:.3f} V"
        f" -> Soil Moisture: {percent:.3f} %"
    )
