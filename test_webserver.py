import os
import pytest
import tempfile
import json
from webserver import app, is_logger_running
from config import PID_FILE
import database

# --- Fixtures ---

@pytest.fixture
def client():
    """Create and configure a new app instance for each test."""
    db_fd, db_path = tempfile.mkstemp()

    app.config['TESTING'] = True
    app.config['DATABASE'] = db_path

    with app.test_client() as client:
        with app.app_context():
            database.DB_FILE = db_path
            database.init_db()
        yield client

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def manage_pid_file():
    """Fixture to manage the PID file for logger status tests."""
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    yield
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

# --- Logger Status and API Tests ---

def test_is_logger_running_when_not_running(manage_pid_file):
    """Test is_logger_running returns False when PID file doesn't exist."""
    assert not is_logger_running()

def test_is_logger_running_with_stale_pid_file(manage_pid_file):
    """Test is_logger_running returns False and cleans up a stale PID file."""
    with open(PID_FILE, "w") as f:
        f.write("99999")  # Non-existent PID
    assert not is_logger_running()
    assert not os.path.exists(PID_FILE)

def test_is_logger_running_when_running(manage_pid_file):
    """Test is_logger_running returns True for a valid PID."""
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    assert is_logger_running()
    assert os.path.exists(PID_FILE)

def test_api_start_stop_logger(client, manage_pid_file):
    """Test starting and stopping the logger via the API."""
    assert not is_logger_running()

    response = client.post('/api/run/start_first')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['ok'] is True
    assert data['running'] is True
    assert is_logger_running()

    response = client.post('/api/run/stop')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['ok'] is True
    assert data['running'] is False
    assert not is_logger_running()

def test_api_log_deletion(client):
    """Test the log deletion API endpoint."""
    with app.app_context():
        database.insert_log(timestamp='2025-01-01_12-00-00', air_temp=25, air_humidity=50, soil_temp=22, soil_raw=1000, soil_voltage=1.5, soil_percent=50, lux=500, stable=1)
        database.insert_log(timestamp='2025-01-01_12-01-00', air_temp=26, air_humidity=51, soil_temp=23, soil_raw=1100, soil_voltage=1.6, soil_percent=55, lux=600, stable=1)
        logs = database.get_logs()
        assert len(logs) == 2

    response = client.post('/api/logs/delete', json={'ids': [1]})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['ok'] is True

    with app.app_context():
        logs = database.get_logs()
        assert len(logs) == 1
        assert logs[0]['id'] == 2

def test_api_relay_toggle(client):
    """Test the relay toggle API endpoint logs events correctly."""
    with app.app_context():
        relay_logs = database.get_relay_log()
        assert len(relay_logs) == 0

    response = client.post('/api/relay/toggle', json={'relay': 1, 'state': True})
    assert response.status_code == 200

    with app.app_context():
        relay_logs = database.get_relay_log()
        assert len(relay_logs) == 1
        assert relay_logs[0]['relay_name'] == 'RELAY1'
        assert relay_logs[0]['action'] == 'ON'