# Chilli - Automated Plant Monitoring & Watering System

**Last updated:** 2025-10-12

## Overview

Chilli is an open-source, Raspberry Pi-powered automated plant monitoring and watering system. It logs sensor data, controls relays for watering/light, and provides a web interface for real-time status, historical data, and hardware control.

## Features

- **Sensor logging:** Monitors soil moisture, air/soil temperature, air humidity, and ambient light (lux).
- **Automated watering:** Triggers a water pump relay based on soil moisture thresholds and cooldowns.
- **Web dashboard:** Flask-based interface to review sensor logs, current relay status, and control hardware.
- **Extensible:** Modular Python code for sensors, relays, hardware interfaces, and database management.
- **Database management:** SQLite-backed log and relay event tables with admin CLI tools.
- **Calibration routines:** CLI support for sensor calibration and database maintenance.

## Technology Stack

- **Python** (core logic, hardware/sensor integration)
- **Flask** (web server and API)
- **HTML/CSS/JavaScript** (web dashboard, static assets)
- **SQLite** (local database)
- **Rich Text Format** (documentation/assets)
- **RPi.GPIO, smbus2, Adafruit libraries** (hardware/sensor drivers)

## Repository Structure

- `config.py` - Central configuration for file paths, GPIO pins, sensor types, intervals, and thresholds.
- `database.py` - SQLite interface, schema migrations, log/relay event insert/delete/query routines.
- `hardware.py` - Hardware initialization and cleanup; configures GPIO, I2C, 1-Wire modules.
- `logger.py` - Main sensor logging loop, auto-watering logic, status file handling, and image cleanup.
- `manage.py` - Command-line tool for hardware/sensor testing, calibration, and database admin.
- `relays.py` - Relay state management and testing routines.
- `sensors.py` - Sensor reading (ADS1115, DHT22, DS18B20, BH1750), calibration, voltage-to-percent conversion.
- `webserver.py` - Flask web server, API endpoints for logs, sensors, relay control, and server status.
- `requirements.txt` - Python dependencies (see below).
- `soil_calibration.json` - Stores calibration values for soil moisture sensor.
- `database.db`, `sensors.db` - SQLite databases for logs and sensor data.
- `static/` - Static web assets (CSS, JS).
    - `static/css/`
    - `static/js/`
- `templates/` - HTML and image files for Flask rendering.
    - `index.html`, `all_data.html`
    - Various favicon and manifest files

## Web Interface

- `/` - Dashboard: latest sensor logs, relay state, logger status.
- `/all_data` - Full historical data view.
- `/api/run/start|stop|status` - Start/stop logger, query logger status.
- `/api/logs` - List recent logs.
- `/api/logs/all` - Filter logs by value/threshold.
- `/api/logs/delete` - Delete logs by ID.
- `/api/sensor/read` - Get current sensor readings.
- `/api/relay/toggle` - Control relay state.
- `/api/relay_log` - List relay event history.
- `/logs/file` - View logger runtime file.

## Setup & Installation

### 1. Dependencies

Install Python 3 and pip, then run:
```
pip install -r requirements.txt
```
For development on non-Raspberry Pi systems:
```
pip install fake-rpi
export FAKE_RPI=1
```

### 2. Hardware

Connect sensors to the specified GPIO pins as per `config.py`:
- **Relay1/2:** Water pump/light
- **DHT22:** Air temp/humidity
- **DS18B20:** Soil temp
- **ADS1115:** Soil moisture
- **BH1750:** Light

### 3. Running the System

- **Logger:** Start via CLI or web interface; periodically logs all sensors and triggers watering.
- **Web Server:** Run `webserver.py` and visit the dashboard in your browser (default port 5000).

### 4. CLI Tools

Use `manage.py` for hardware tests, sensor calibration, and database queries/deletes:
```
python3 manage.py <command> [options]
```
Commands:
- `test_ads`, `test_dht`, `test_ds18b20`, `test_relays`, `test_bh1750`
- `calibrate_ads --dry|--wet`
- `get_sql`, `delete_sql --all|--ids <ID(s)>`

## Requirements

See [`requirements.txt`](https://github.com/NeedleStacker/chilli/blob/main/requirements.txt):
- Flask
- adafruit-blinka
- adafruit-circuitpython-ads1x15
- Adafruit_Python_DHT
- smbus2
- RPi.GPIO
- fake-rpi (for non-RPi dev)

## License

*No license specified yet.*

## Author

[NeedleStacker](https://github.com/NeedleStacker)

---

**Language composition:**  
Rich Text Format (71.6%), Python (15.7%), JavaScript (6.6%), HTML (5.7%), CSS (0.4%)
