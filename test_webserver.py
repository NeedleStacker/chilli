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
    # Create a temporary file for the database
    db_fd, db_path = tempfile.mkstemp()

    # Configure the app for testing
    app.config['TESTING'] = True
    app.config['DATABASE'] = db_path

    with app.test_client() as client:
        with app.app_context():
            # Initialize the temporary database
            database.DB_FILE = db_path
            database.init_db()
        yield client

    # Clean up the temporary database file
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

# --- Logger Status Tests (existing) ---

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


# --- New API Tests ---

def test_api_log_deletion(client):
    """Test the log deletion API endpoint."""
    # 1. Add some dummy data to the database
    with app.app_context():
        database.insert_log('2025-01-01_12-00-00', 25, 50, 22, 1000, 1.5, 50, 500, 1)
        database.insert_log('2025-01-01_12-01-00', 26, 51, 23, 1100, 1.6, 55, 600, 1)
        database.insert_log('2025-01-01_12-02-00', 27, 52, 24, 1200, 1.7, 60, 700, 1)
        logs = database.get_logs()
        assert len(logs) == 3

    # 2. Test deleting a single log entry
    response = client.post('/api/logs/delete', json={'ids': [2]})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['ok'] is True
    assert "Obrisano 1 zapisa" in data['msg']

    with app.app_context():
        logs = database.get_logs()
        assert len(logs) == 2
        assert all(log['id'] != 2 for log in logs)

    # 3. Test deleting all remaining logs
    response = client.post('/api/logs/delete', json={'ids': ['all']})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['ok'] is True
    assert "Obrisano svi zapisa" in data['msg']

    with app.app_context():
        logs = database.get_logs()
        assert len(logs) == 0

def test_api_relay_toggle(client):
    """Test the relay toggle API endpoint logs events correctly."""
    # 1. Ensure the relay log is initially empty
    with app.app_context():
        relay_logs = database.get_relay_log()
        assert len(relay_logs) == 0

    # 2. Toggle Relay 1 ON
    response = client.post('/api/relay/toggle', json={'relay': 1, 'state': True})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['ok'] is True
    assert data['relay'] == 'RELAY1'
    assert data['state'] == 'ON'

    # 3. Verify the event was logged to the database
    with app.app_context():
        relay_logs = database.get_relay_log()
        assert len(relay_logs) == 1
        assert relay_logs[0]['relay_name'] == 'RELAY1'
        assert relay_logs[0]['action'] == 'ON'
        assert relay_logs[0]['source'] == 'web'