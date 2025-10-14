import os
import json
import time
import datetime
from typing import Tuple, Optional, Dict

import smbus2
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_ads1x15.ads1115 as ADS

from config import CALIB_FILE, device_file, DHT_SENSOR, DHT_PIN, i2c as shared_i2c

def read_soil_raw_shared() -> Tuple[Optional[int], Optional[float]]:
    """
    Reads the raw soil moisture value and voltage from the ADS1115 sensor using the shared I2C bus.

    Returns:
        Tuple[Optional[int], Optional[float]]: Raw ADC value and voltage, or (None, None) on failure.
    """
    if not shared_i2c:
        return None, None
    ads = ADS.ADS1115(shared_i2c)
    ads.gain = 1
    return _read_ads_once(ads)


def read_soil_raw_fresh() -> Tuple[Optional[int], Optional[float]]:
    """
    Reads the raw soil moisture value and voltage from the ADS1115 sensor by creating a new I2C object.

    Returns:
        Tuple[Optional[int], Optional[float]]: Raw ADC value and voltage, or (None, None) on failure.
    """
    try:
        import board
        import busio
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c)
        ads.gain = 1
        raw, voltage = _read_ads_once(ads)
        del ads
        del i2c
        return raw, voltage
    except Exception as e:
        print(f"[WARN] fresh ADS read error: {e}")
        return None, None


def read_ds18b20_temp() -> Optional[float]:
    """
    Reads the soil temperature from the DS18B20 sensor.

    Returns:
        Optional[float]: The temperature in Celsius, or None if the read fails.
    """
    if not device_file:
        return None
    try:
        with open(device_file, 'r') as f:
            lines = f.readlines()
        if lines[0].strip()[-3:] != 'YES':
            return None
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp_string = lines[1][equals_pos + 2:]
            return float(temp_string) / 1000.0
    except Exception:
        return None
    return None


def load_calibration() -> Dict[str, float]:
    """
    Loads voltage calibration data from the JSON file.

    Returns:
        Dict[str, float]: A dictionary with 'dry_v' and 'wet_v' keys.
    """
    defDryV = 1.60
    defWetV = 0.20
    if not os.path.exists(CALIB_FILE):
        print("[WARN] Calibration file not found -> using defaults")
        return {"dry_v": defDryV, "wet_v": defWetV}

    try:
        with open(CALIB_FILE, "r") as f:
            obj = json.load(f)
        if "dry_v" in obj and "wet_v" in obj:
            return {"dry_v": float(obj["dry_v"]), "wet_v": float(obj["wet_v"])}
        if "dry" in obj and "wet" in obj:  # Legacy format support
            print("[WARN] Found old RAW calibration; using default V limits (1.60/0.20V)")
        return {"dry_v": defDryV, "wet_v": defWetV}
    except Exception as e:
        print(f"[ERROR] Failed to read calibration file: {e} -> using defaults")
        return {"dry_v": defDryV, "wet_v": defWetV}


def _read_ads_once(ads: ADS.ADS1115) -> Tuple[int, float]:
    """
    Performs a stable read from the ADS1115 ADC.

    Args:
        ads (ADS.ADS1115): The ADS1115 object.

    Returns:
        Tuple[int, float]: The raw ADC value and the corresponding voltage.
    """
    chan = AnalogIn(ads, ADS.P0)
    _ = chan.value
    time.sleep(0.05)
    raw = chan.value
    voltage = chan.voltage
    return raw, voltage


def read_soil_raw() -> Tuple[Optional[int], Optional[float]]:
    """
    Reads the raw soil moisture value and voltage from the ADS1115 sensor.
    """
    try:
        import board
        import busio
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c)
        ads.gain = 1
        raw, voltage = _read_ads_once(ads)
        return raw, voltage
    except Exception as e:
        print(f"[WARN] fresh ADS read error: {e}")
        return None, None


def read_soil_percent_from_voltage(voltage: Optional[float], debug: bool = False) -> float:
    """
    Converts soil moisture sensor voltage to a percentage based on calibration values.

    Args:
        voltage (Optional[float]): The voltage to convert.
        debug (bool): If True, prints debugging information.

    Returns:
        float: The calculated soil moisture percentage (0-100).
    """
    calib = load_calibration()
    dry_v = float(calib["dry_v"])
    wet_v = float(calib["wet_v"])

    if dry_v < wet_v:
        dry_v, wet_v = wet_v, dry_v

    span = dry_v - wet_v
    if span <= 0:
        if debug:
            print(f"[DEBUG] Invalid calibration span: dry_v={dry_v}, wet_v={wet_v}")
        return 0.0

    if voltage is None:
        return 0.0

    if voltage >= dry_v:
        percent = 0.0
    elif voltage <= wet_v:
        percent = 100.0
    else:
        percent = (dry_v - voltage) * 100.0 / span

    percent = max(0.0, min(100.0, percent))
    if debug:
        print(f"[DEBUG] voltage={voltage:.4f}, dry_v={dry_v:.4f}, wet_v={wet_v:.4f}, span={span:.4f}, percent={percent:.3f}")
    return round(percent, 3)


def read_soil_percent(raw: Optional[int] = None, voltage: Optional[float] = None, debug: bool = False) -> float:
    """
    A wrapper to get the soil moisture percentage.

    If voltage is not provided, it will be read from the sensor first.
    """
    if voltage is None:
        _, voltage = read_soil_raw()
    return read_soil_percent_from_voltage(voltage, debug=debug)


BH1750_ADDR = 0x23
BH1750_MODE = 0x10


def read_bh1750_lux() -> Optional[float]:
    """
    Reads the ambient light intensity in Lux from the BH1750 sensor.

    Returns:
        Optional[float]: The light intensity in Lux, or None on failure.
    """
    try:
        bus = smbus2.SMBus(1)
        bus.write_byte(BH1750_ADDR, BH1750_MODE)
        time.sleep(0.2)
        data = bus.read_i2c_block_data(BH1750_ADDR, BH1750_MODE, 2)
        lux = (data[0] << 8 | data[1]) / 1.2
        return round(lux, 2)
    except Exception as e:
        print(f"[WARN] BH1750 očitanje nije uspjelo: {e}")
        return None


def test_dht() -> Tuple[Optional[float], Optional[float]]:
    """
    Reads temperature and humidity from the DHT22 sensor.

    Returns:
        Tuple[Optional[float], Optional[float]]: Temperature (C) and humidity (%), or (None, None).
    """
    try:
        import Adafruit_DHT
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        return temperature, humidity
    except Exception:
        return None, None


def test_ds18b20() -> Optional[float]:
    """
    Reads the soil temperature from the DS18B20 sensor.
    """
    return read_ds18b20_temp()


def test_ads() -> None:
    """Tests the ADS1115 sensor and prints the readings."""
    raw, voltage = read_soil_raw()
    pct = read_soil_percent_from_voltage(voltage, debug=True)
    print(f"ADS1115 channel 0: raw={raw}, voltage={0.0 if voltage is None else round(voltage,3)} V - {datetime.datetime.now()}")
    print(f"Soil moisture: {pct:.3f} %")


def calibrate_ads(dry: bool = False, wet: bool = False) -> None:
    """
    Saves new calibration values for the soil moisture sensor.

    Args:
        dry (bool): If True, sets the current reading as the dry reference.
        wet (bool): If True, sets the current reading as the wet reference.
    """
    raw, voltage = read_soil_raw()
    if voltage is None:
        print("[ERROR] Nije moguće očitati ADS1115.")
        return

    calib = load_calibration()
    if dry:
        calib["dry_v"] = float(voltage)
        print(f"Snima se DRY referenca (V): {voltage:.3f} V  [raw={raw}]")
    if wet:
        calib["wet_v"] = float(voltage)
        print(f"Snima se WET referenca (V): {voltage:.3f} V  [raw={raw}]")
    with open(CALIB_FILE, "w") as f:
        json.dump(calib, f)
    print("Kalibracija spremljena:", calib)
