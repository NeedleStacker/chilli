import board
import busio
import RPi.GPIO as GPIO
import os

# Import pin and setting configurations
from config import RELAY1, RELAY2, DHT_PIN

# Global I2C variable so other modules can use it
i2c = None

def initialize(app_mode='main'):
    """Initializes the hardware components for the Raspberry Pi.

    This function sets up the GPIO mode, configures relay pins as outputs,
    loads necessary kernel modules for 1-Wire communication (for DS18B20),
    and initializes the I2C bus.

    Args:
        app_mode (str): The mode in which the application is running.
                        This argument is currently not used but is intended
                        for future differentiation between modes like 'main'
                        (full hardware access) and 'util' (limited access).
    """
    global i2c
    print("[HARDWARE] Initializing hardware...")

    # --- GPIO ---
    # Use BCM pin numbering
    GPIO.setmode(GPIO.BCM)

    # --- Relays ---
    # Set pins as outputs and turn them off (LOW-trigger relays are OFF at HIGH)
    GPIO.setup(RELAY1, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(RELAY2, GPIO.OUT, initial=GPIO.HIGH)
    print(f"[HARDWARE] Relays {RELAY1}, {RELAY2} set as OUT, state: OFF.")

    # --- DS18B20 ---
    # Load kernel modules required for 1-Wire
    os.system('modprobe w1-gpio')
    os.system('modprobe w1-therm')
    print("[HARDWARE] 1-Wire modules (w1-gpio, w1-therm) loaded.")

    # --- I2C ---
    # Initialize the I2C bus only once
    if i2c is None:
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            print("[HARDWARE] I2C bus initialized.")
        except Exception as e:
            print(f"[ERROR] Failed to initialize I2C: {e}")
            i2c = None

    print("[HARDWARE] Initialization complete.")


def cleanup():
    """Cleans up GPIO resources.

    This function should be called on application exit to release all GPIO
    pins and prevent warnings or conflicts on subsequent runs.
    """
    print("[HARDWARE] Cleaning up GPIO resources.")
    GPIO.cleanup()