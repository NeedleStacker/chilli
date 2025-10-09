import os
import json
import time
import glob
import random
import hardware # Uvozimo naš hardverski modul

# Moduli projekta
from config import (
    CALIB_FILE, W1_BASE_DIR, BH1750_ADDR,
    DHT_SENSOR, DHT_PIN, DEV_MODE
)

# --- Biblioteke koje se koriste samo ako DEV_MODE = False ---
# Inicijaliziramo ih na None da možemo provjeravati njihovu dostupnost
smbus2, Adafruit_DHT, ADS, AnalogIn = None, None, None, None

if not DEV_MODE:
    try:
        import smbus2 as real_smbus2
        smbus2 = real_smbus2
    except ImportError:
        print("[WARN] 'smbus2' biblioteka nije pronađena. BH1750 senzor neće raditi.")

    try:
        import Adafruit_DHT as real_Adafruit_DHT
        Adafruit_DHT = real_Adafruit_DHT
    except ImportError:
        print("[WARN] 'Adafruit_DHT' biblioteka nije pronađena. DHT22 senzor neće raditi.")

    try:
        from adafruit_ads1x15.analog_in import AnalogIn as real_AnalogIn
        from adafruit_ads1x15 import ads1115 as real_ADS
        AnalogIn, ADS = real_AnalogIn, real_ADS
    except ImportError:
        print("[WARN] 'adafruit-circuitpython-ads1x15' biblioteka nije pronađena. ADS1115 senzor vlage neće raditi.")


# --- Glavne funkcije za očitavanje senzora ---

def read_soil_raw(retries=3, delay=0.1):
    """Čita sirovu vrijednost i napon s ADS1115 senzora vlage s pokušajima."""
    if DEV_MODE:
        fake_voltage = random.uniform(0.5, 2.5)
        fake_raw = int(fake_voltage * 10000)
        return fake_raw, fake_voltage

    if not all([ADS, AnalogIn, hardware.i2c]):
        print("[ERROR] ADS1115 biblioteka ili I2C sabirnica nije dostupna.")
        return None, None

    for attempt in range(retries):
        try:
            ads = ADS.ADS1115(hardware.i2c)
            ads.gain = 1
            chan = AnalogIn(ads, ADS.P0)
            _ = chan.value
            time.sleep(0.05)
            return chan.value, chan.voltage
        except Exception as e:
            print(f"[WARN] Pokušaj {attempt + 1}/{retries} neuspješan za ADS1115: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
    print(f"[ERROR] Svi pokušaji čitanja s ADS1115 neuspješni.")
    return None, None

def read_ds18b20_temp(retries=3, delay=0.1):
    """Čita temperaturu s DS18B20 senzora s pokušajima."""
    if DEV_MODE:
        return random.uniform(18.0, 22.0)

    for attempt in range(retries):
        try:
            device_folders = glob.glob(os.path.join(W1_BASE_DIR, '28-*'))
            if not device_folders:
                if attempt == 0: print("[WARN] DS18B20 nije pronađen.")
                return None
            device_file = os.path.join(device_folders[0], 'w1_slave')
            with open(device_file, 'r') as f:
                lines = f.readlines()
            if lines[0].strip()[-3:] == 'YES':
                equals_pos = lines[1].find('t=')
                if equals_pos != -1:
                    return float(lines[1][equals_pos + 2:]) / 1000.0
        except Exception as e:
            print(f"[WARN] Pokušaj {attempt + 1}/{retries} neuspješan za DS18B20: {e}")
        if attempt < retries - 1:
            time.sleep(delay)
    print(f"[ERROR] Svi pokušaji čitanja s DS18B20 neuspješni.")
    return None

def read_bh1750_lux(retries=3, delay=0.2):
    """Čita osvjetljenje s BH1750 senzora s pokušajima."""
    if DEV_MODE:
        return random.uniform(100.0, 1500.0)

    if not smbus2:
        print("[ERROR] 'smbus2' biblioteka nije dostupna za BH1750.")
        return None

    bus = None
    for attempt in range(retries):
        try:
            bus = smbus2.SMBus(1)
            bus.write_byte(BH1750_ADDR, 0x10)
            time.sleep(0.2)
            data = bus.read_i2c_block_data(BH1750_ADDR, 0, 2)
            lux = (data[0] << 8 | data[1]) / 1.2
            bus.close()
            return lux
        except Exception as e:
            print(f"[WARN] Pokušaj {attempt + 1}/{retries} neuspješan za BH1750: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
        finally:
            if bus:
                bus.close()
    print(f"[ERROR] Svi pokušaji čitanja s BH1750 neuspješni.")
    return None

def test_dht():
    """Očitava DHT22 senzor."""
    if DEV_MODE:
        return random.uniform(23.0, 27.0), random.uniform(40.0, 60.0)

    if not Adafruit_DHT or not hardware.GPIO:
        print("[ERROR] Adafruit_DHT biblioteka ili GPIO nije dostupan.")
        return None, None

    try:
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        return temperature, humidity
    except Exception as e:
        print(f"[WARN] DHT22 očitavanje nije uspjelo: {e}")
        return None, None

# --- Kalibracija i izračun postotka ---

def load_calibration():
    """Učitava kalibracijske vrijednosti."""
    defaults = {"dry_v": 1.60, "wet_v": 0.20}
    if not os.path.exists(CALIB_FILE): return defaults
    try:
        with open(CALIB_FILE, "r") as f: calib = json.load(f)
        if "dry_v" in calib and "wet_v" in calib:
            return {"dry_v": float(calib["dry_v"]), "wet_v": float(calib["wet_v"])}
        return defaults
    except Exception:
        return defaults

def read_soil_percent_from_voltage(voltage):
    """Pretvara napon senzora vlage u postotak."""
    if voltage is None: return 0.0
    calib = load_calibration()
    dry_v, wet_v = calib["dry_v"], calib["wet_v"]
    if dry_v < wet_v: dry_v, wet_v = wet_v, dry_v
    span = dry_v - wet_v
    if span <= 0: return 0.0
    percent = 100 * (dry_v - voltage) / span
    return max(0.0, min(100.0, percent))

# --- Funkcije za testiranje iz komandne linije ---

def test_ds18b20():
    temp = read_ds18b20_temp()
    print(f"DS18B20 Temperatura: {temp:.2f}°C" if temp is not None else "DS18B20: Neuspješno očitavanje.")

def test_ads():
    raw, voltage = read_soil_raw()
    if raw is not None:
        pct = read_soil_percent_from_voltage(voltage)
        print(f"ADS1115: Raw={raw}, Voltage={voltage:.3f}V -> {pct:.2f}%")
    else:
        print("ADS1115: Neuspješno očitavanje.")

def calibrate_ads(dry=False, wet=False):
    """Sprema kalibracijske vrijednosti."""
    if not dry and not wet: print("Koristi --dry ili --wet."); return
    raw, voltage = read_soil_raw()
    if voltage is None: print("[ERROR] Nije moguće očitati ADS1115."); return
    calib = load_calibration()
    if dry: calib["dry_v"] = voltage; print(f"Spremljena 'SUHA' referenca: {voltage:.3f}V")
    if wet: calib["wet_v"] = voltage; print(f"Spremljena 'MOKRA' referenca: {voltage:.3f}V")
    try:
        with open(CALIB_FILE, "w") as f: json.dump(calib, f, indent=4)
        print("Kalibracija uspješno spremljena.")
    except IOError as e:
        print(f"[ERROR] Nije moguće spremiti kalibracijsku datoteku: {e}")