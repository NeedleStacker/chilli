import os

# Support a development stub to allow running on non-RPi hosts
USE_STUB = os.environ.get('USE_STUB_HARDWARE') == '1'

# Try to import hardware libraries lazily; tests may inject a fake `hardware`
# module via `tests/conftest.py` so keep top-level imports minimal.
try:
    if not USE_STUB:
        import board  # type: ignore
        import busio  # type: ignore
        import RPi.GPIO as GPIO  # type: ignore
    else:
        # We'll use the dev stub instead of real hardware
        from dev_stub_hardware import initialize as _stub_init, cleanup as _stub_cleanup
        board = None
        busio = None
        GPIO = None
except Exception:
    # Don't raise here; defer errors until initialize() so module import is safe
    board = None
    busio = None
    GPIO = None

# Import pin and setting configurations
from config import RELAY1, RELAY2, DHT_PIN

# Global I2C variable so other modules can use it
i2c = None

def initialize(app_mode='main'):
    """Initializes the hardware components for the Raspberry Pi.

    This function sets up the GPIO mode, configures relay pins as outputs,
    loads necessary kernel modules for 1-Wire communication (for DS18B20),
    and initializes the I2C bus.

    If the required platform libraries are not available, this function will
    print a helpful message and leave `i2c` as None. For CI/dev on non-RPi
    hosts, set the environment variable `USE_STUB_HARDWARE=1` to use the
    `dev_stub_hardware.py` no-op implementation.
    """
    global i2c, board, busio, GPIO

    if USE_STUB:
        # Prefer the dev stub when requested
        try:
            from dev_stub_hardware import initialize as _stub_init
            _stub_init(app_mode=app_mode)
            i2c = None
            return
        except Exception as e:
            print(f"[HARDWARE] Failed to initialize dev stub: {e}")

    # If platform modules were not importable earlier, attempt to import now
    if board is None or busio is None or GPIO is None:
        try:
            import board as _board  # type: ignore
            import busio as _busio  # type: ignore
            import RPi.GPIO as _GPIO  # type: ignore
            board = _board
            busio = _busio
            GPIO = _GPIO
        except Exception as e:
            print("[ERROR] Hardware libraries not available."
                  " Install 'adafruit-blinka' (pip3 install adafruit-blinka)"
                  " or set USE_STUB_HARDWARE=1 to use the dev stub.")
            print(f"[ERROR] Detailed import error: {e}")
            return

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
    if USE_STUB:
        try:
            from dev_stub_hardware import cleanup as _stub_cleanup
            _stub_cleanup()
            return
        except Exception:
            pass

    if GPIO is None:
        print("[HARDWARE] GPIO not available; skipping cleanup.")
        return

    print("[HARDWARE] Cleaning up GPIO resources.")
    GPIO.cleanup()