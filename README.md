# Chili Plant Automation System

This project provides a complete system for monitoring and automating the care of a chili plant using a Raspberry Pi. It periodically logs environmental data, controls a water pump based on soil moisture, and provides a web interface for visualization and manual control.

## Features

- **Sensor Monitoring**: Tracks air temperature, humidity, soil temperature, soil moisture, and ambient light levels.
- **Automated Watering**: Automatically activates a water pump when soil moisture drops below a configurable threshold.
- **Data Logging**: Stores all sensor readings in an SQLite database for historical analysis.
- **Web Dashboard**: A Flask-based web interface to view real-time and historical data, and to see the status of system components.
- **Manual Control**: Toggle relays for the water pump and a light directly from the web UI.
- **API Access**: A simple REST API to programmatically access sensor data and control relays.
- **Command-Line Interface**: A utility script (`manage.py`) for easy testing of hardware components and database management.

## Hardware Requirements

- Raspberry Pi (tested on a Pi 4, but any model with GPIO pins should work).
- **Sensors**:
    - DHT22: Air temperature and humidity.
    - DS18B20 (waterproof): Soil temperature.
    - Capacitive Soil Moisture Sensor.
    - ADS1115 ADC: To read analog values from the soil moisture sensor.
    - BH1750: Ambient light sensor.
- **Actuators**:
    - 2-Channel 5V Relay Module.
    - Small 5V water pump.
    - (Optional) LED light or other device for the second relay.
- Breadboard and jumper wires for connections.

## Software Setup

### 1. Prepare the Raspberry Pi

First, ensure your Raspberry Pi is running the latest Raspberry Pi OS. Then, enable the necessary hardware interfaces:

1.  Run `sudo raspi-config`.
2.  Navigate to `Interface Options`.
3.  Enable both `I2C` and `1-Wire`.
4.  Reboot the Pi when prompted.

### 2. Clone the Repository

Clone this project onto your Raspberry Pi:
```bash
git clone https://github.com/your-username/chili-automation.git
cd chili-automation
```

### 3. Install Dependencies

Install system-level packages and create a Python virtual environment.

```bash
# Update package lists
sudo apt-get update

# Install required system libraries
sudo apt-get install -y python3-pip python3-dev python3-venv

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt
```
> **Note**: If you encounter issues installing `Adafruit_Python_DHT`, you may need to install it with a specific flag: `pip install Adafruit_Python_DHT --config-settings="--build-option=--force-pi"`

## Running the Application

### 1. Calibrate the Soil Moisture Sensor

For accurate readings, you must first calibrate the soil moisture sensor.

1.  Place the sensor in completely dry soil.
2.  Run the calibration command:
    ```bash
    python3 manage.py calibrate_ads --dry
    ```
3.  Place the sensor in fully saturated (wet) soil.
4.  Run the calibration command again:
    ```bash
    python3 manage.py calibrate_ads --wet
    ```
    This saves the reference values to `soil_calibration.json`.

### 2. Start the Web Server

The main application is launched via the Flask web server. This server provides the UI and automatically starts the background logger process.

```bash
python3 webserver.py
```

Once running, you can access the web interface by navigating to `http://<your-pi-ip-address>:5000` in a web browser on the same network.

## Using the Management Tool (`manage.py`)

The `manage.py` script is a powerful command-line tool for testing and administration.

**Usage**: `python3 manage.py <command> [options]`

**Commands**:
- `test_ads`: Read and display data from the soil moisture sensor.
- `test_dht`: Read and display data from the air temperature/humidity sensor.
- `test_ds18b20`: Read and display data from the soil temperature sensor.
- `test_bh1750`: Read and display data from the light sensor.
- `test_relays`: Sequentially turn both relays on and off.
- `calibrate_ads`: Calibrate the soil sensor. Use with `--dry` or `--wet`.
- `get_sql`: Print all sensor data from the database.
- `delete_sql`: Delete records from the database.
    - Use `--ids "1,5,10"` to delete specific records.
    - Use `--ids "5-10"` to delete a range of records.
    - Use `--all` to delete all records (requires confirmation).

## Project Structure

```
.
├── config.py             # Central configuration for pins, addresses, and settings.
├── database.py           # Handles all SQLite database interactions.
├── hardware.py           # Low-level hardware initialization (GPIO, I2C).
├── logger.py             # Background process for logging data and auto-watering.
├── manage.py             # CLI tool for testing and administration.
├── README.md             # This file.
├── relays.py             # Functions to control the relay module.
├── requirements.txt      # Python dependencies.
├── sensors.db            # SQLite database file (created on first run).
├── sensors.py            # Functions for reading from all sensors.
├── soil_calibration.json # Stores moisture sensor calibration data.
├── static/               # CSS and JS for the web interface.
├── templates/            # HTML templates for the web interface.
└── webserver.py          # Main Flask application, UI, and API.
```