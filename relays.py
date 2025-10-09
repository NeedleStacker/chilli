from config import DEV_MODE, RELAY1, RELAY2
import hardware  # Uvozimo naš hardverski modul
import time

def set_relay_state(relay_pin, state):
    """
    Postavlja stanje određenog releja, ako je GPIO dostupan.
    Args:
        relay_pin (int): GPIO pin releja.
        state (bool): True za ON (uključeno), False za OFF (isključeno).
    """
    if DEV_MODE:
        print(f"[DEV_MODE] Relej na pinu {relay_pin} postavljen na {'ON' if state else 'OFF'}")
        return

    if not hardware.GPIO:
        print(f"[WARN] GPIO nije dostupan. Ne mogu postaviti stanje za relej na pinu {relay_pin}.")
        return

    # Logika za LOW-trigger releje
    hardware.GPIO.output(relay_pin, hardware.GPIO.LOW if state else hardware.GPIO.HIGH)

def get_relay_state(relay_pin):
    """
    Provjerava stanje određenog releja, ako je GPIO dostupan.
    Returns:
        bool: True ako je relej ON (uključen), inače False.
    """
    if DEV_MODE:
        # U DEV_MODE, pretpostavimo da su releji uvijek isključeni
        return False

    if not hardware.GPIO:
        # Ako GPIO nije dostupan, vrati zadano stanje (isključeno)
        return False

    # Za LOW-trigger relej, stanje je ON (True) kada je GPIO pin na LOW (0).
    return hardware.GPIO.input(relay_pin) == hardware.GPIO.LOW

def test_relays():
    """
    Sekvencijalno testira oba releja kako bi se provjerila njihova funkcionalnost.
    """
    if not hardware.GPIO:
        print("[WARN] GPIO nije dostupan. Preskačem testiranje releja.")
        return

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