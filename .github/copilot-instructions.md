# Copilot Instructions for Chili Plant Automation System

This guide helps AI coding agents work productively in this codebase. It summarizes architecture, workflows, and conventions specific to this project.

## Architecture Overview
- **Main Components:**
  - `webserver.py`: Flask web app, REST API, and UI. Starts background logger.
  - `logger.py`: Background process for periodic sensor logging and auto-watering.
  - `hardware.py`: GPIO/I2C hardware setup and initialization.
  - `sensors.py`: Sensor reading functions (DHT22, DS18B20, BH1750, ADS1115).
  - `relays.py`: Relay control functions for pump/light.
  - `database.py`: SQLite database operations for sensor data.
  - `manage.py`: CLI tool for hardware tests, calibration, and DB admin.
- **Data Flow:**
  - Sensor readings → `logger.py` → `database.py` (SQLite)
  - Web UI/API (`webserver.py`) reads from DB and controls relays
  - Manual/auto relay control via web or CLI

## Developer Workflows
- **Setup:**
  - Use Python 3. Create a virtual environment and install dependencies from `requirements.txt`.
  - Enable I2C and 1-Wire on Raspberry Pi for hardware access.
- **Running:**
  - Start the web server: `python3 webserver.py`
  - Use `manage.py` for hardware tests, calibration, and DB management (see README for commands).
- **Calibration:**
  - Calibrate soil moisture sensor with `python3 manage.py calibrate_ads --dry` and `--wet`. Stores values in `soil_calibration.json`.
- **Database:**
  - Sensor data stored in `sensors.db`. Use `manage.py get_sql`/`delete_sql` for inspection and cleanup.

## Project Conventions
- **Configuration:**
  - All hardware pin mappings, addresses, and thresholds are in `config.py`.
- **Patterns:**
  - Hardware access is abstracted in `hardware.py` and `sensors.py`.
  - Relay control is always via `relays.py`.
  - Data logging and auto-watering logic is in `logger.py` (not in the web server).
  - Web UI templates are in `templates/`, static assets in `static/`.
- **Testing:**
  - Use CLI commands in `manage.py` for hardware and DB tests. No formal unit tests present.

## Integration Points
- **External Dependencies:**
  - Adafruit sensor libraries, Flask, SQLite, and other Python packages (see `requirements.txt`).
- **Hardware:**
  - Designed for Raspberry Pi GPIO/I2C. Sensor and relay models are specified in README.

## Examples
- To read soil moisture: `python3 manage.py test_ads`
- To manually water: Use web UI or `python3 manage.py test_relays`
- To view historical data: Access web UI or use `manage.py get_sql`

## Key Files
- `config.py`, `hardware.py`, `sensors.py`, `relays.py`, `logger.py`, `database.py`, `webserver.py`, `manage.py`, `soil_calibration.json`, `sensors.db`

---
If any section is unclear or missing, please provide feedback for improvement.

## Immediate gotchas (must-read for agents)
- `hardware.initialize()` runs at import time in `webserver.py` and performs GPIO/I2C initialization. Avoid importing `hardware` in analysis-only contexts unless you guard or mock hardware access.
- `webserver.py` spawns `logger.py` as a subprocess and expects `logger.py run` to be available; `logger.py` also manipulates files like `STATUS_FILE` and `logger_run.log`.
- Many modules call hardware or OS APIs (GPIO, I2C, `modprobe`, `/dev` access) directly — use `hardware.i2c` and the functions in `hardware.py` as the single initialization point.
- Database schema migrations are performed in `database.init_db()` on startup; tests that create or modify `sensors.db` may trigger migrations.

## Short refactor recommendations (prioritized, low-risk first)
1. Defer hardware initialization to runtime: change `webserver.py` to not call `hardware.initialize()` at import time. Instead, initialize during app startup (`if __name__ == '__main__'` or an `app.before_first_request` handler). This makes static analysis, unit tests, and CI safe.
  - Files: `webserver.py`, `hardware.py`.
  - Risk: low. Small code movement and a change in app startup ordering.

2. Extract long-running subprocess management into a small utility module (e.g., `process_manager.py`) used by `webserver.py`. Right now `webserver.py` manages locks, subprocesses, and status files inline.
  - Files: `webserver.py`.
  - Risk: low–medium. Improves testability.

3. Add explicit dependency and runtime checks: create a small `dev_stub_hardware.py` that exports the same symbols as `hardware.py` but with no GPIO usage, and use it in CI to run lint/type checks and unit tests on non-RPi hosts.
  - Files: new `dev_stub_hardware.py`, CI config (optional).
  - Risk: low. Makes the project portable to Windows/macOS CI.

4. Centralize configuration and constants into `config.py` (already present) but annotate with comments and default fallbacks for desktop development (e.g., `USE_STUB_HARDWARE = os.environ.get('USE_STUB_HARDWARE')`). This complements the dev stub.
  - Files: `config.py` (small edits).

5. Improve database concurrency: `database.py` currently opens short-lived connections which is fine for SQLite, but consider using a connection factory or context manager wrappers (or `check_same_thread=False` only if multi-threaded). Add simple retry logic for DBLocked errors during writes.
  - Files: `database.py`.
  - Risk: medium.

6. Add unit-test examples for pure logic (calibration math, percent calculation). Create `tests/test_sensors.py` with a test for `read_soil_percent_from_voltage()` using sample calibration JSON.
  - Files: `sensors.py`, `soil_calibration.json` (read-only), new `tests/` files.
  - Risk: low.

## Code pointers & examples
- To avoid hardware side-effects in analysis or tests, import the API surface only:
  - Use `from hardware import i2c` or `from sensors import read_soil_percent_from_voltage` (pure function) instead of importing top-level modules that trigger side-effects.
- Example: move `hardware.initialize()` call from top-level in `webserver.py` to a startup function:
  - At top of `webserver.py`: remove `hardware.initialize()` and `database.init_db()` calls.
  - Add:
   - an `app.before_first_request` function that calls `hardware.initialize()` and `database.init_db()`.

## Next steps I can perform
- Implement the small `app.before_first_request` change in `webserver.py` and add a `dev_stub_hardware.py` file to make the repository testable on Windows. (Low-risk edits.)
- Add a single unit test for the soil-percent math and a small `pytest` dev dependency entry in `requirements-dev.txt`.

If you'd like, I can apply the low-risk changes now (defer init and add a hardware stub + unit test). Which would you prefer me to do next?