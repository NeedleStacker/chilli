import json
import os
import tempfile
import sys
import types


# --- Insert lightweight fake modules for hardware and sensor libraries ---
def _inject_fakes():
    # Minimal fake 'hardware' module (prevents imports of board/RPi.GPIO)
    hw = types.ModuleType('hardware')
    hw.i2c = None
    def initialize(app_mode='main'):
        return None
    def cleanup():
        return None
    hw.initialize = initialize
    hw.cleanup = cleanup
    sys.modules['hardware'] = hw

    # Fake smbus2 with an SMBus class
    smbus2 = types.ModuleType('smbus2')
    class SMBus:
        def __init__(self, *a, **k):
            pass
        def write_byte(self, *a, **k):
            pass
        def read_i2c_block_data(self, addr, reg, length):
            return [0, 0]
        def close(self):
            pass
    smbus2.SMBus = SMBus
    sys.modules['smbus2'] = smbus2

    # Fake Adafruit_DHT with read_retry
    Adafruit_DHT = types.ModuleType('Adafruit_DHT')
    # Provide a DHT22 constant used by config.py
    Adafruit_DHT.DHT22 = object()
    def read_retry(sensor, pin):
        return (50.0, 25.0)  # humidity, temperature
    Adafruit_DHT.read_retry = read_retry
    sys.modules['Adafruit_DHT'] = Adafruit_DHT

    # Fake adafruit_ads1x15 modules (ads1115 and analog_in)
    ads_mod = types.ModuleType('adafruit_ads1x15')
    ads1115 = types.ModuleType('adafruit_ads1x15.ads1115')
    class ADS1115:
        P0 = 0
        def __init__(self, i2c):
            pass
    ads1115.ADS1115 = ADS1115
    analog_in = types.ModuleType('adafruit_ads1x15.analog_in')
    class AnalogIn:
        def __init__(self, ads, pin):
            self.value = 12345
            self.voltage = 1.234
    analog_in.AnalogIn = AnalogIn
    sys.modules['adafruit_ads1x15'] = ads_mod
    sys.modules['adafruit_ads1x15.ads1115'] = ads1115
    sys.modules['adafruit_ads1x15.analog_in'] = analog_in


_inject_fakes()

import sensors


def test_read_soil_percent_from_voltage_basic():
    # Use temporary calibration values by writing a small json file
    tmp_calib = {"dry_v": 1.6, "wet_v": 0.2}
    tf = tempfile.NamedTemporaryFile(delete=False, mode='w')
    try:
        json.dump(tmp_calib, tf)
        tf.close()
        # Point sensors to this calibration file by monkeypatching the CALIB_FILE path
        orig_calib = getattr(sensors, 'CALIB_FILE', None)
        sensors.CALIB_FILE = tf.name

        # Midpoint voltage should give ~50%
        midpoint = (tmp_calib['dry_v'] + tmp_calib['wet_v']) / 2
        pct = sensors.read_soil_percent_from_voltage(midpoint)
        assert 45.0 <= pct <= 55.0
    finally:
        try:
            os.unlink(tf.name)
        except Exception:
            pass
        if orig_calib is not None:
            sensors.CALIB_FILE = orig_calib
