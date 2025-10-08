import RPi.GPIO as GPIO
import time
from config import RELAY1, RELAY2

def set_relay_state(relay_pin, state):
    """
    Postavlja stanje određenog releja.
    Args:
        relay_pin (int): GPIO pin releja.
        state (bool): True za ON (uključeno), False za OFF (isključeno).
                      Logika je za LOW-trigger releje.
    """
    GPIO.output(relay_pin, GPIO.LOW if state else GPIO.HIGH)

def get_relay_state(relay_pin):
    """
    Provjerava stanje određenog releja.
    Args:
        relay_pin (int): GPIO pin releja.
    Returns:
        bool: True ako je relej ON (uključen), inače False.
    """
    # Za LOW-trigger relej, stanje je ON (True) kada je GPIO pin na LOW (0).
    return GPIO.input(relay_pin) == GPIO.LOW

def test_relays():
    """
    Sekvencijalno testira oba releja kako bi se provjerila njihova funkcionalnost.
    """
    print("Testiranje releja...")
    try:
        print("Relej 1 -> ON, Relej 2 -> OFF")
        set_relay_state(RELAY1, True)
        set_relay_state(RELAY2, False)
        time.sleep(2)

        print("Relej 1 -> OFF, Relej 2 -> ON")
        set_relay_state(RELAY1, False)
        set_relay_state(RELAY2, True)
        time.sleep(2)
    finally:
        # Osiguraj da su oba releja isključena na kraju testa
        print("Oba releja -> OFF")
        set_relay_state(RELAY1, False)
        set_relay_state(RELAY2, False)
        print("Test završen.")