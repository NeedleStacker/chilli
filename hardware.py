import os
from config import DEV_MODE, RELAY1, RELAY2

# Definicija varijabli na razini modula, inicijalno None
board, busio, GPIO = None, None, None

# Uvezi hardverske biblioteke samo ako nismo u razvojnom modu
if not DEV_MODE:
    try:
        import board as real_board
        import busio as real_busio
        import RPi.GPIO as real_GPIO
        board, busio, GPIO = real_board, real_busio, real_GPIO
        print("[HARDWARE] Hardverske biblioteke (board, busio, RPi.GPIO) uspješno uvezene.")
    except (ImportError, RuntimeError) as e:
        print(f"[WARN] Nije moguće uvesti hardverske biblioteke: {e}. Hardverske funkcije će biti onemogućene.")

# Globalna varijabla za I2C, kako bi je drugi moduli mogli koristiti
i2c = None

def initialize():
    """
    Centralna funkcija za inicijalizaciju hardvera.
    Pokušava inicijalizirati svaki dio zasebno.
    """
    global i2c
    print("[HARDWARE] Inicijalizacija hardvera...")

    if DEV_MODE:
        print("[HARDWARE] DEV_MODE je UKLJUČEN. Preskačem stvarnu inicijalizaciju hardvera.")
        return

    # --- GPIO ---
    if GPIO:
        try:
            GPIO.setmode(GPIO.BCM)
            # --- Releji ---
            GPIO.setup(RELAY1, GPIO.OUT, initial=GPIO.HIGH)
            GPIO.setup(RELAY2, GPIO.OUT, initial=GPIO.HIGH)
            print(f"[HARDWARE] Releji {RELAY1}, {RELAY2} postavljeni kao OUT, stanje: OFF.")
        except Exception as e:
            print(f"[ERROR] Greška pri inicijalizaciji GPIO: {e}")
    else:
        print("[WARN] RPi.GPIO nije dostupan. Releji i DHT senzor neće raditi.")

    # --- DS18B20 ---
    try:
        # ovi commandi ne rade na ne-pi sustavu i vracaju gresku
        # os.system('modprobe w1-gpio')
        # os.system('modprobe w1-therm')
        print("[HARDWARE] 1-Wire moduli (w1-gpio, w1-therm) se pretpostavljaju učitanima.")
    except Exception as e:
        print(f"[ERROR] Greška pri učitavanju 1-Wire modula: {e}")

    # --- I2C ---
    if busio and board:
        if i2c is None:
            try:
                i2c = busio.I2C(board.SCL, board.SDA)
                print("[HARDWARE] I2C sabirnica inicijalizirana.")
            except Exception as e:
                print(f"[ERROR] Neuspjela inicijalizacija I2C: {e}")
                i2c = None
    else:
        print("[WARN] 'busio' ili 'board' biblioteka nije dostupna. I2C senzori neće raditi.")
        i2c = None

    print("[HARDWARE] Inicijalizacija završena.")


def cleanup():
    """
    Čisti GPIO resurse. Preskače ako je DEV_MODE uključen ili GPIO nije dostupan.
    """
    if DEV_MODE or not GPIO:
        return
    print("[HARDWARE] Čišćenje GPIO resursa.")
    GPIO.cleanup()