#relays.py
import RPi.GPIO as GPIO
import time
from config import RELAY1, RELAY2

def init_relays():
    """Postavlja početno stanje releja na OFF."""
    set_relay_state(RELAY1, False)
    set_relay_state(RELAY2, False)

def set_relay_state(relay, state):
    """Postavlja stanje releja (True=ON, False=OFF). LOW-trigger logika."""
    GPIO.output(relay, GPIO.LOW if state else GPIO.HIGH)

def get_relay_state(relay):
    """Vrati True ako je relej uključen (LOW-trigger), False ako je isključen."""
    return GPIO.input(relay) == GPIO.LOW

def test_relays():
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

    print(f"Stanje Relej1: {'ON' if get_relay_state(RELAY1) else 'OFF'}, Relej2: {'ON' if get_relay_state(RELAY2) else 'OFF'}")
    print("Test završen.")

def set_all_relays(state):
    """Postavlja oba releja na isto stanje."""
    set_relay_state(RELAY1, state)
    set_relay_state(RELAY2, state)

def get_all_relays():
    """Vrati dict sa stanjem oba releja."""
    return {
        "relay1": get_relay_state(RELAY1),
        "relay2": get_relay_state(RELAY2)
    }
