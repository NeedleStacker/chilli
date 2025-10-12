import os
import json
import time
import glob
import smbus2
import Adafruit_DHT

# Moduli projekta
import hardware  # Za pristup inicijaliziranom hardware.i2c
from config import (
    CALIB_FILE, W1_BASE_DIR, BH1750_ADDR,
    DHT_SENSOR, DHT_PIN
)

# Adafruit biblioteke za ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_ads1x15.ads1115 as ADS


# --- Privatna pomoćna funkcija za ADS1115 ---
def _read_ads_once(ads_instance):
    """
    Izvršava jedno stabilno očitanje s ADS1115.
    Uključuje 'flush' korak za stabilizaciju očitanja.
    """
    chan = AnalogIn(ads_instance, ADS.P0)
    _ = chan.value  # Prvo očitanje za "buđenje" kanala
    time.sleep(0.05)
    raw = chan.value
    voltage = chan.voltage
    return raw, voltage


# --- Glavne funkcije za očitavanje senzora ---

def read_soil_raw():
    """
    Čita sirovu vrijednost i napon s ADS1115 senzora vlage.
    Koristi globalnu I2C sabirnicu inicijaliziranu u 'hardware.py'.
    """
    if hardware.i2c is None:
        print("[ERROR] I2C sabirnica nije inicijalizirana. Ne mogu očitati senzor vlage.")
        return None, None
    try:
        ads = ADS.ADS1115(hardware.i2c)
        ads.gain = 1
        return _read_ads_once(ads)
    except Exception as e:
        print(f"[ERROR] Greška pri čitanju s ADS1115: {e}")
        return None, None


def _get_ds18b20_device_file():
    """Pronađi datoteku 1-Wire uređaja. Vraća putanju ili None."""
    try:
        # Traži direktorij koji počinje s '28-'
        device_folders = glob.glob(os.path.join(W1_BASE_DIR, '28-*'))
        if not device_folders:
            print("[WARN] DS18B20 senzor nije pronađen (nema '28-*' direktorija).")
            return None
        # Vrati punu putanju do 'w1_slave' datoteke
        return os.path.join(device_folders[0], 'w1_slave')
    except Exception as e:
        print(f"[ERROR] Greška pri traženju DS18B20 uređaja: {e}")
        return None


def read_ds18b20_temp():
    """Čita temperaturu s DS18B20 senzora. Vraća temperaturu u °C ili None."""
    device_file = _get_ds18b20_device_file()
    if not device_file:
        return None

    try:
        with open(device_file, 'r') as f:
            lines = f.readlines()

        # Provjeri CRC (cyclic redundancy check)
        if lines[0].strip()[-3:] != 'YES':
            print("[WARN] DS18B20 CRC provjera neuspjela.")
            return None

        # Pronađi temperaturu u drugom redu
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp_string = lines[1][equals_pos + 2:]
            return float(temp_string) / 1000.0
    except (IOError, IndexError, ValueError) as e:
        print(f"[ERROR] Greška pri čitanju temperature s DS18B20: {e}")
        return None


def read_bh1750_lux():
    """Čita osvjetljenje u luksima s BH1750 senzora."""
    try:
        # Mod za kontinuirano mjerenje visoke rezolucije
        BH1750_MODE = 0x10
        bus = smbus2.SMBus(1)  # Koristi /dev/i2c-1
        bus.write_byte(BH1750_ADDR, BH1750_MODE)
        time.sleep(0.2) # Pričekaj da senzor obavi mjerenje
        data = bus.read_i2c_block_data(BH1750_ADDR, 0, 2)
        lux = (data[0] << 8 | data[1]) / 1.2
        bus.close()
        return lux
    except Exception as e:
        print(f"[WARN] BH1750 očitavanje nije uspjelo: {e}")
        return None


def test_dht():
    """Očitava DHT22 senzor. Vraća tuple (temperatura, vlaga) ili (None, None)."""
    try:
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        return temperature, humidity
    except Exception as e:
        print(f"[WARN] DHT22 očitavanje nije uspjelo: {e}")
        return None, None


# --- Kalibracija i izračun postotka ---

def load_calibration():
    """Učitava kalibracijske vrijednosti (suho/mokro) iz JSON datoteke."""
    defaults = {"dry_v": 1.60, "wet_v": 0.20}
    if not os.path.exists(CALIB_FILE):
        print("[WARN] Kalibracijska datoteka nije pronađena, koristim zadane vrijednosti.")
        return defaults
    try:
        with open(CALIB_FILE, "r") as f:
            calib = json.load(f)
        # Osiguraj da postoje ispravni ključevi
        if "dry_v" in calib and "wet_v" in calib:
            return {"dry_v": float(calib["dry_v"]), "wet_v": float(calib["wet_v"])}
        else:
            print("[WARN] Ključevi 'dry_v' i 'wet_v' nisu pronađeni, koristim zadane vrijednosti.")
            return defaults
    except (json.JSONDecodeError, TypeError) as e:
        print(f"[ERROR] Greška pri čitanju kalibracijske datoteke: {e}. Koristim zadane vrijednosti.")
        return defaults


def read_soil_percent_from_voltage(voltage, debug=False):
    """Pretvara napon senzora vlage u postotak (0-100%)."""
    if voltage is None:
        return 0.0

    calib = load_calibration()
    dry_v, wet_v = calib["dry_v"], calib["wet_v"]

    # Osiguraj da je dry_v uvijek veća vrijednost
    if dry_v < wet_v:
        dry_v, wet_v = wet_v, dry_v

    span = dry_v - wet_v
    if span <= 0:
        return 0.0

    # Izračun postotka
    percent = 100 * (dry_v - voltage) / span
    percent = max(0.0, min(100.0, percent)) # Ograniči na 0-100

    if debug:
        print(f"[DEBUG] V={voltage:.3f}V, Dry={dry_v}V, Wet={wet_v}V -> {percent:.2f}%")

    return percent


# --- Funkcije za testiranje iz komandne linije ---

def test_ds18b20():
    """Testira DS18B20 senzor i ispisuje rezultat."""
    temp = read_ds18b20_temp()
    if temp is not None:
        print(f"DS18B20 Temperatura: {temp:.2f}°C")
    else:
        print("DS18B20: Neuspješno očitavanje.")


def test_ads():
    """Testira ADS1115 senzor i ispisuje rezultat."""
    raw, voltage = read_soil_raw()
    if raw is not None:
        pct = read_soil_percent_from_voltage(voltage, debug=True)
        print(f"ADS1115: Raw={raw}, Voltage={voltage:.3f}V")
        print(f"Izračunata vlaga: {pct:.2f}%")
    else:
        print("ADS1115: Neuspješno očitavanje.")


def calibrate_ads(dry=False, wet=False):
    """Sprema kalibracijske vrijednosti za senzor vlage."""
    if not dry and not wet:
        print("Nije odabrana opcija. Koristi --dry ili --wet.")
        return

    raw, voltage = read_soil_raw()
    if voltage is None:
        print("[ERROR] Nije moguće očitati ADS1115 za kalibraciju.")
        return

    calib = load_calibration()
    if dry:
        calib["dry_v"] = voltage
        print(f"Spremljena 'SUHA' referenca: {voltage:.3f}V")
    if wet:
        calib["wet_v"] = voltage
        print(f"Spremljena 'MOKRA' referenca: {voltage:.3f}V")

    try:
        with open(CALIB_FILE, "w") as f:
            json.dump(calib, f, indent=4)
        print("Kalibracija uspješno spremljena.")
    except IOError as e:
        print(f"[ERROR] Nije moguće spremiti kalibracijsku datoteku: {e}")