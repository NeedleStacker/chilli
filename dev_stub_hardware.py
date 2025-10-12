"""
Development stub for `hardware.py` so the repository can be imported and
unit-tested on non-Raspberry Pi hosts.

This file mimics the public API of `hardware.py` used by other modules:
- `i2c` (None or a simple placeholder)
- `initialize()`
- `cleanup()`

Usage (example in test/CI):
- Set the environment variable `USE_STUB_HARDWARE=1` and in test bootstrapping
  swap imports or modify `sys.path` so `dev_stub_hardware` is used instead of
  `hardware`.

Note: This stub does not attempt to emulate real hardware readings. Use it
only for tests that don't require actual sensors.
"""

import os

# Placeholder for the I2C bus object used by sensors.py
i2c = None


def initialize(app_mode='main'):
    """No-op initialize for CI/dev environments."""
    print("[DEV_STUB] initialize() called - no hardware initialized.")


def cleanup():
    """No-op cleanup for CI/dev environments."""
    print("[DEV_STUB] cleanup() called.")
