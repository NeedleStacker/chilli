"""Pytest bootstrapping: inject fake modules for non-RPi environments.

This file inserts lightweight fake modules into `sys.modules` so tests can
import `sensors`, `hardware`, and other modules without having to install
RPi-specific packages.

If you prefer to run integration/hardware tests against a real Raspberry Pi,
run pytest in an environment where the real hardware packages are installed
and remove or modify this file.
"""

import sys
import types


def _inject_fakes():
    # Minimal fake 'hardware' module
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

    # Fake Adafruit_DHT with read_retry and DHT22
    Adafruit_DHT = types.ModuleType('Adafruit_DHT')
    Adafruit_DHT.DHT22 = object()
    def read_retry(sensor, pin):
        return (50.0, 25.0)  # humidity, temperature
    Adafruit_DHT.read_retry = read_retry
    sys.modules['Adafruit_DHT'] = Adafruit_DHT

    # Fake adafruit_ads1x15 modules (ads1115 and analog_in)
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
    sys.modules['adafruit_ads1x15.ads1115'] = ads1115
    sys.modules['adafruit_ads1x15.analog_in'] = analog_in


_inject_fakes()
