from config import DEV_MODE, RELAY1, RELAY2
import time

if not DEV_MODE:
    try:
        import RPi.GPIO as GPIO
    except (ImportError, RuntimeError) as e:
        raise ImportError(f"Nije moguće uvesti RPi.GPIO: {e}. "
                          "Postavite DEV_MODE=True u config.py za rad bez hardvera.")

def set_relay_state(relay_pin, state):
    """
    Postavlja stanje određenog releja.
    Args:
        relay_pin (int): GPIO pin releja.
        state (bool): True za ON (uključeno), False za OFF (isključeno).
    """
    if DEV_MODE:
        print(f"[DEV_MODE] Relej na pinu {relay_pin} postavljen na {'ON' if state else 'OFF'}")
        return

    # Logika za LOW-trigger releje
    GPIO.output(relay_pin, GPIO.LOW if state else GPIO.HIGH)

def get_relay_state(relay_pin):
    """
    Provjerava stanje određenog releja.
    Returns:
        bool: True ako je relej ON (uključen), inače False.
    """
    if DEV_MODE:
        # U DEV_MODE, pretpostavimo da su releji uvijek isključeni
        return False

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