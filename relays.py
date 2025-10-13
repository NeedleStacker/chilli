import time
from config import RELAY1, RELAY2

# Import RPi.GPIO if available; otherwise set to None for dev/CI environments
try:
    import RPi.GPIO as GPIO
except Exception:
    GPIO = None

def set_relay_state(relay_pin, state):
    """Sets the state of a specific relay.

    This function controls a relay connected to a GPIO pin. It is designed
    for LOW-trigger relays, where setting the pin to LOW turns the relay ON,
    and setting it to HIGH turns it OFF.

    Args:
        relay_pin (int): The GPIO pin number for the relay.
        state (bool): The desired state of the relay. True for ON (active),
                      False for OFF (inactive).
    """
    if GPIO is None:
        print(f"[RELAYS] GPIO not available; skipping set_relay_state({relay_pin}, {state})")
        return
    try:
        GPIO.output(relay_pin, GPIO.LOW if state else GPIO.HIGH)
    except RuntimeError as e:
        print(f"[RELAYS] Failed to set relay {relay_pin}: {e}")

def get_relay_state(relay_pin):
    """Gets the current state of a specific relay.

    This function reads the input level of the GPIO pin connected to the relay
    to determine its state. It assumes a LOW-trigger relay, where a LOW signal
    means the relay is ON.

    Args:
        relay_pin (int): The GPIO pin number for the relay.

    Returns:
        bool: True if the relay is ON (pin is LOW), False otherwise.
    """
    if GPIO is None:
        print(f"[RELAYS] GPIO not available; get_relay_state({relay_pin}) -> False")
        return False
    try:
        return GPIO.input(relay_pin) == GPIO.LOW
    except RuntimeError as e:
        # Happens if channel wasn't set up; return False and warn
        print(f"[RELAYS] GPIO input failed for pin {relay_pin}: {e}")
        return False

def test_relays():
    """Sequentially tests both relays to verify their functionality.

    This function cycles through turning each relay on and off with a delay,
    allowing for a visual or functional check of the connected hardware.
    It ensures both relays are turned off at the end of the test.
    """
    print("Testing relays...")
    try:
        print("Relay 1 -> ON, Relay 2 -> OFF")
        set_relay_state(RELAY1, True)
        set_relay_state(RELAY2, False)
        time.sleep(2)

        print("Relay 1 -> OFF, Relay 2 -> ON")
        set_relay_state(RELAY1, False)
        set_relay_state(RELAY2, True)
        time.sleep(2)
    finally:
        # Ensure both relays are turned off at the end of the test
        print("Both relays -> OFF")
        set_relay_state(RELAY1, False)
        set_relay_state(RELAY2, False)
        print("Test complete.")