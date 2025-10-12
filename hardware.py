import board
import busio
import RPi.GPIO as GPIO
import os

# Import pinova i postavki iz glavne konfiguracije
from config import RELAY1, RELAY2, DHT_PIN

# Globalna varijabla za I2C, kako bi je drugi moduli mogli koristiti
i2c = None

def initialize(app_mode='main'):
    """
    Centralna funkcija za inicijalizaciju hardvera.
    'main' mode: za logger ili webserver koji koriste sve komponente.
    'util': za skripte koje ne trebaju sve (npr. samo GPIO).
    """
    global i2c
    print("[HARDWARE] Inicijalizacija hardvera...")

    # --- GPIO ---
    # Koristi se BCM numeriranje pinova
    GPIO.setmode(GPIO.BCM)

    # --- Releji ---
    # Postavi pinove kao izlazne i ugasi ih (LOW-trigger releji su OFF na HIGH)
    GPIO.setup(RELAY1, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(RELAY2, GPIO.OUT, initial=GPIO.HIGH)
    print(f"[HARDWARE] Releji {RELAY1}, {RELAY2} postavljeni kao OUT, stanje: OFF.")

    # --- DS18B20 ---
    # Učitaj module kernela potrebne za 1-Wire
    os.system('modprobe w1-gpio')
    os.system('modprobe w1-therm')
    print("[HARDWARE] 1-Wire moduli (w1-gpio, w1-therm) učitani.")

    # --- I2C ---
    # Inicijaliziraj I2C sabirnicu samo jednom
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
    Čisti GPIO resurse. Pozvati na kraju izvođenja programa.
    """
    print("[HARDWARE] Čišćenje GPIO resursa.")
    GPIO.cleanup()