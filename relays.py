import RPi.GPIO as GPIO
import time
from typing import Dict

from config import RELAY1_PIN, RELAY2_PIN

def initialize_relays() -> None:
    """Sets the initial state of both relays to OFF."""
    set_relay_state(RELAY1_PIN, False)
    set_relay_state(RELAY2_PIN, False)

def set_relay_state(pin: int, is_on: bool) -> None:
    """
    Sets the state of a specific relay pin.
    Assumes LOW-trigger logic (LOW = ON, HIGH = OFF).

    Args:
        pin (int): The GPIO pin number of the relay.
        is_on (bool): True to turn the relay ON, False to turn it OFF.
    """
    GPIO.output(pin, GPIO.LOW if is_on else GPIO.HIGH)

def get_relay_state(pin: int) -> bool:
    """
    Returns the current state of a relay.

    Args:
        pin (int): The GPIO pin number of the relay.

    Returns:
        bool: True if the relay is ON, False if it is OFF.
    """
    return GPIO.input(pin) == GPIO.LOW

def test_relays() -> None:
    """Runs a test sequence to toggle both relays."""
    print("Testing relays...")
    print("Relay 1 ON, Relay 2 OFF")
    set_relay_state(RELAY1_PIN, True)
    set_relay_state(RELAY2_PIN, False)
    time.sleep(2)

    print("Relay 1 OFF, Relay 2 ON")
    set_relay_state(RELAY1_PIN, False)
    set_relay_state(RELAY2_PIN, True)
    time.sleep(2)

    print("Both relays OFF")
    set_relay_state(RELAY1_PIN, False)
    set_relay_state(RELAY2_PIN, False)

    print(
        f"Final state: Relay 1: {'ON' if get_relay_state(RELAY1_PIN) else 'OFF'}, "
        f"Relay 2: {'ON' if get_relay_state(RELAY2_PIN) else 'OFF'}"
    )
    print("Test complete.")

def set_all_relays(is_on: bool) -> None:
    """Sets both relays to the same state."""
    set_relay_state(RELAY1_PIN, is_on)
    set_relay_state(RELAY2_PIN, is_on)

def get_all_relays() -> Dict[str, bool]:
    """
    Returns a dictionary with the current state of both relays.

    Returns:
        Dict[str, bool]: A dictionary mapping relay names to their ON/OFF state.
    """
    return {
        "relay1": get_relay_state(RELAY1_PIN),
        "relay2": get_relay_state(RELAY2_PIN),
    }
