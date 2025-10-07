import os
import json
import time
import datetime
import board
import busio
import smbus2

from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_ads1x15.ads1115 as ADS

from config import CALIB_FILE, device_file, DHT_SENSOR, DHT_PIN, i2c as shared_i2c


def read_soil_raw_shared():
    """
    Čita koristeći shared I2C iz configa (brže, ali kod tebe je drugo i treće
    očitanje znalo 'podivljati').
    """
    ads = ADS.ADS1115(shared_i2c)
    ads.gain = 1
    return _read_ads_once(ads)


def read_soil_raw_fresh():
    """
    Svaki put stvori NOVI I2C i NOVI ADS1115 objekt → ponaša se kao 'prvo mjerenje'.
    Ovo je rješenje za tvoj slučaj.
    """
    try:
        import board
        import busio
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c)
        ads.gain = 1
        raw, voltage = _read_ads_once(ads)
        # Po Blinki najčešće nema deinit; samo pusti GC da počisti
        del ads
        del i2c
        return raw, voltage
    except Exception as e:
        print(f"[WARN] fresh ADS read error: {e}")
        return None, None

# ------------------ DS18B20 ------------------
def read_ds18b20_temp():
    """Vrati temperaturu tla ili None ako čitanje ne uspije."""
    try:
        with open(device_file, 'r') as f:
            lines = f.readlines()
        if lines[0].strip()[-3:] != 'YES':
            return None
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp_string = lines[1][equals_pos + 2:]
            return float(temp_string) / 1000.0
    except Exception:
        return None


# ------------------ Kalibracija (volt-based) ------------------
def load_calibration():
    """
    Očekuje kalibraciju u voltima:
        {"dry_v": 1.60, "wet_v": 0.20}
    Ako nema, pokušat će pročitati staro (RAW) i samo vratiti default V granice.
    """
    defDryV = 1.60
    defWetV = 0.20
    if not os.path.exists(CALIB_FILE):
        print("[WARN] Calibration file not found -> using defaults")
        return {"dry_v": defDryV, "wet_v": defWetV}

    try:
        with open(CALIB_FILE, "r") as f:
            obj = json.load(f)
        if "dry_v" in obj and "wet_v" in obj:
            return {"dry_v": float(obj["dry_v"]), "wet_v": float(obj["wet_v"])}
        # fallback na stari RAW format → samo default
        if "dry" in obj and "wet" in obj:
            print("[WARN] Found old RAW calibration; using default V limits (1.60/0.20V)")
        return {"dry_v": defDryV, "wet_v": defWetV}
    except Exception as e:
        print(f"[ERROR] Failed to read calibration file: {e} -> using defaults")
        return {"dry_v": defDryV, "wet_v": defWetV}


# ------------------ ADS1115 čitanje ------------------
def _read_ads_once(ads):
    """Jedno stabilno očitanje s 'flush' korakom."""
    chan = AnalogIn(ads, ADS.P0)
    _ = chan.value
    time.sleep(0.05)
    raw = chan.value
    voltage = chan.voltage
    return raw, voltage


def read_soil_raw():
    """
    Svaki put inicijalizira novi I2C i ADS1115 → ponaša se kao 'prvo mjerenje'.
    Ovo rješava problem gdje su druga i treća očitanja znala 'podivljati'.
    """
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c)
        ads.gain = 1
        raw, voltage = _read_ads_once(ads)
        return raw, voltage
    except Exception as e:
        print(f"[WARN] fresh ADS read error: {e}")
        return None, None


# ------------------ Postotak vlage (iz VOLTAGE) ------------------
def read_soil_percent_from_voltage(voltage, debug=False):
    calib = load_calibration()
    dry_v = float(calib["dry_v"])
    wet_v = float(calib["wet_v"])

    if dry_v < wet_v:
        dry_v, wet_v = wet_v, dry_v

    span = dry_v - wet_v
    if span <= 0:
        if debug:
            print(f"[DEBUG] Invalid calibration span: dry_v={dry_v}, wet_v={wet_v}")
        return 0.0

    if voltage is None:
        return 0.0

    if voltage >= dry_v:
        percent = 0.0
    elif voltage <= wet_v:
        percent = 100.0
    else:
        percent = (dry_v - voltage) * 100.0 / span

    percent = max(0.0, min(100.0, percent))
    if debug:
        print(f"[DEBUG] voltage={voltage:.4f}, dry_v={dry_v:.4f}, wet_v={wet_v:.4f}, span={span:.4f}, percent={percent:.3f}")
    return round(percent, 3)


def read_soil_percent(raw=None, voltage=None, debug=False):
    """
    Kompatibilni wrapper: koristi voltage ako ga dobiješ,
    ako ne → očitaj ga.
    """
    if voltage is None:
        _, voltage = read_soil_raw()
    return read_soil_percent_from_voltage(voltage, debug=debug)

# -----------------------------
# BH1750 - svjetlosni senzor
# -----------------------------
BH1750_ADDR = 0x23  # ili 0x5C, ovisi o ADO pinu
BH1750_MODE = 0x10  # kontinurani high-res (1 lx rezolucija)

def read_bh1750_lux():
    """Vrati izmjerenu svjetlost u luksima s BH1750 senzora."""
    try:
        bus = smbus2.SMBus(1)  # /dev/i2c-1
        bus.write_byte(BH1750_ADDR, BH1750_MODE)
        time.sleep(0.2)
        data = bus.read_i2c_block_data(BH1750_ADDR, BH1750_MODE, 2)
        lux = (data[0] << 8 | data[1]) / 1.2
        return round(lux, 2)
    except Exception as e:
        print(f"[WARN] BH1750 očitanje nije uspjelo: {e}")
        return None

# ------------------ Test / kalibracija ------------------
def test_dht():
    """Vrati tuple (temperature, humidity) ili (None, None)."""
    try:
        import Adafruit_DHT
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        return temperature, humidity
    except Exception:
        return None, None


def test_ds18b20():
    """Vrati temperaturu ili None."""
    return read_ds18b20_temp()


def test_ads():
    raw, voltage = read_soil_raw()
    pct = read_soil_percent_from_voltage(voltage, debug=True)
    print(f"ADS1115 channel 0: raw={raw}, voltage={0.0 if voltage is None else round(voltage,3)} V - {datetime.datetime.now()}")
    print(f"Soil moisture: {pct:.3f} %")


def calibrate_ads(dry=False, wet=False):
    raw, voltage = read_soil_raw()
    if voltage is None:
        print("[ERROR] Nije moguće očitati ADS1115.")
        return

    calib = load_calibration()
    if dry:
        calib["dry_v"] = float(voltage)
        print(f"Snima se DRY referenca (V): {voltage:.3f} V  [raw={raw}]")
    if wet:
        calib["wet_v"] = float(voltage)
        print(f"Snima se WET referenca (V): {voltage:.3f} V  [raw={raw}]")
    with open(CALIB_FILE, "w") as f:
        json.dump(calib, f)
    print("Kalibracija spremljena:", calib)
