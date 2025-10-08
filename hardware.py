import os
from config import DEV_MODE, RELAY1, RELAY2

# Uvezi hardverske biblioteke samo ako nismo u razvojnom modu
if not DEV_MODE:
    try:
        import board
        import busio
        import RPi.GPIO as GPIO
    except (ImportError, RuntimeError) as e:
        # Podigni iznimku umjesto izlaska, kako bi se aplikacija mogla testirati
        raise ImportError(f"Nije moguće uvesti hardverske biblioteke: {e}. "
                          "Postavite DEV_MODE=True u config.py za rad bez hardvera.")

# Globalna varijabla za I2C, kako bi je drugi moduli mogli koristiti
i2c = None

def initialize():
    """
    Centralna funkcija za inicijalizaciju hardvera.
    Preskače sve ako je DEV_MODE uključen.
    """
    global i2c
    print("[HARDWARE] Inicijalizacija hardvera...")

    if DEV_MODE:
        print("[HARDWARE] DEV_MODE je UKLJUČEN. Preskačem stvarnu inicijalizaciju hardvera.")
        return

    # --- GPIO ---
    GPIO.setmode(GPIO.BCM)

    # --- Releji ---
    GPIO.setup(RELAY1, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(RELAY2, GPIO.OUT, initial=GPIO.HIGH)
    print(f"[HARDWARE] Releji {RELAY1}, {RELAY2} postavljeni kao OUT, stanje: OFF.")

    # --- DS18B20 ---
    os.system('modprobe w1-gpio')
    os.system('modprobe w1-therm')
    print("[HARDWARE] 1-Wire moduli (w1-gpio, w1-therm) učitani.")

    # --- I2C ---
    if i2c is None:
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            print("[HARDWARE] I2C sabirnica inicijalizirana.")
        except Exception as e:
            print(f"[ERROR] Neuspjela inicijalizacija I2C: {e}")
            i2c = None

    print("[HARDWARE] Inicijalizacija završena.")


def cleanup():
    """
    Čisti GPIO resurse. Preskače ako je DEV_MODE uključen.
    """
    if DEV_MODE:
        return
    print("[HARDWARE] Čišćenje GPIO resursa.")
    GPIO.cleanup()