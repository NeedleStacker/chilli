import argparse

# Moduli projekta
import hardware
import sensors
import database
from relays import test_relays

def main():
    """
    Glavna funkcija za izvršavanje naredbi iz komandne linije.
    """
    parser = argparse.ArgumentParser(
        description="Alat za upravljanje i testiranje sustava za navodnjavanje.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    # Definicija svih dostupnih naredbi
    parser.add_argument(
        "command",
        choices=[
            "test_ads", "test_dht", "test_ds18b20", "test_relays", "test_bh1750",
            "calibrate_ads", "get_sql", "delete_sql"
        ],
        help="""Naredba za izvršavanje:
  - test_ads: Testira senzor vlage tla (ADS1115).
  - test_dht: Testira senzor temperature i vlage zraka (DHT22).
  - test_ds18b20: Testira senzor temperature tla (DS18B20).
  - test_relays: Testira oba releja.
  - test_bh1750: Testira senzor svjetlosti (BH1750).
  - calibrate_ads: Kalibrira senzor vlage.
  - get_sql: Dohvaća i ispisuje sve zapise iz baze.
  - delete_sql: Briše zapise iz baze.
"""
    )

    # Opcionalni argumenti
    parser.add_argument("--dry", action="store_true", help="Za calibrate_ads: postavlja 'suhu' referentnu vrijednost.")
    parser.add_argument("--wet", action="store_true", help="Za calibrate_ads: postavlja 'mokru' referentnu vrijednost.")
    parser.add_argument("--all", action="store_true", help="Za delete_sql: briše SVE zapise iz tablice 'logs'.")
    parser.add_argument("--ids", type=str, help="Za delete_sql: specificira ID-eve za brisanje (npr. '1,2,5' ili '3-10').")

    args = parser.parse_args()

    # Inicijalizacija hardvera je potrebna za većinu naredbi
    print("Inicijaliziram hardver...")
    hardware.initialize()
    print("-" * 20)

    try:
        # Izvršavanje odabrane naredbe
        if args.command == "test_ads":
            sensors.test_ads()
        elif args.command == "test_dht":
            temp, hum = sensors.test_dht()
            if temp is not None and hum is not None:
                print(f"DHT22: Temperatura={temp:.2f}°C, Vlažnost={hum:.2f}%")
            else:
                print("DHT22: Neuspješno očitavanje.")
        elif args.command == "test_ds18b20":
            sensors.test_ds18b20()
        elif args.command == "test_bh1750":
            lux = sensors.read_bh1750_lux()
            if lux is not None:
                print(f"BH1750 Osvjetljenje: {lux:.2f} lx")
            else:
                print("BH1750: Neuspješno očitavanje.")
        elif args.command == "test_relays":
            test_relays()
        elif args.command == "calibrate_ads":
            sensors.calibrate_ads(dry=args.dry, wet=args.wet)
        elif args.command == "get_sql":
            database.get_sql_data()
        elif args.command == "delete_sql":
            # Potvrda za brisanje svega
            if args.all:
                confirm = input("⚠️  Jeste li sigurni da želite obrisati SVE podatke iz baze? (da/ne): ")
                if confirm.lower() != 'da':
                    print("Otkazano.")
                    return

            database.delete_sql_data(ids=args.ids, delete_all=args.all)

    except Exception as e:
        print(f"\nDogodila se greška: {e}")
    finally:
        # Osiguraj da se resursi uvijek oslobode
        print("-" * 20)
        print("Čistim hardverske resurse...")
        hardware.cleanup()
        print("Gotovo.")

if __name__ == "__main__":
    main()