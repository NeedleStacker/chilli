import RPi.GPIO as GPIO
import time
from typing import Dict

from config import RELAY1, RELAY2

def init_relays() -> None:
    """Sets the initial state of both relays to OFF."""
    set_relay_state(RELAY1, False)
    set_relay_state(RELAY2, False)

def set_relay_state(relay: int, state: bool) -> None:
    """
    Sets the state of a specific relay pin.
    Assumes LOW-trigger logic (LOW = ON, HIGH = OFF).

    Args:
        relay (int): The GPIO pin number of the relay.
        state (bool): True to turn the relay ON, False to turn it OFF.
    """
    GPIO.output(relay, GPIO.LOW if state else GPIO.HIGH)

def get_relay_state(relay: int) -> bool:
    """
    Returns the current state of a relay.

    Args:
        relay (int): The GPIO pin number of the relay.

    Returns:
        bool: True if the relay is ON, False if it is OFF.
    """
    return GPIO.input(relay) == GPIO.LOW

def test_relays() -> None:
    """Runs a test sequence to toggle both relays."""
    print("Testiranje releja...")
    print("Relej 1 ON, Relej 2 OFF")
    set_relay_state(RELAY1, True)
    set_relay_state(RELAY2, False)
    time.sleep(2)

    print("Relej 1 OFF, Relej 2 ON")
    set_relay_state(RELAY1, False)
    set_relay_state(RELAY2, True)
    time.sleep(2)

    print("Oba releja OFF")
    set_relay_state(RELAY1, False)
    set_relay_state(RELAY2, False)

    print(
        f"Stanje Relej1: {'ON' if get_relay_state(RELAY1) else 'OFF'}, "
        f"Relej2: {'ON' if get_relay_state(RELAY2) else 'OFF'}"
    )
    print("Test završen.")

def set_all_relays(state: bool) -> None:
    """Sets both relays to the same state."""
    set_relay_state(RELAY1, state)
    set_relay_state(RELAY2, state)

def get_all_relays() -> Dict[str, bool]:
    """
    Returns a dictionary with the current state of both relays.

    Returns:
        Dict[str, bool]: A dictionary mapping relay names to their ON/OFF state.
    """
    return {
        "relay1": get_relay_state(RELAY1),
        "relay2": get_relay_state(RELAY2),
    }
