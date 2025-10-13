
import os
import sqlite3
import tempfile
import pytest
from database import get_logs, get_relay_log, init_db, _get_db_connection

# Fixture to set up a temporary database file for testing
@pytest.fixture
def temp_db(monkeypatch):
    # Create a temporary file to act as the database
    fd, db_path = tempfile.mkstemp()
    os.close(fd)

    # Monkeypatch the DB_FILE constant in the database module
    monkeypatch.setattr('database.DB_FILE', db_path)

    # Initialize the database schema in the temporary file
    init_db()

    # Add some dummy data
    conn = _get_db_connection()
    c = conn.cursor()
    # Insert 20 log entries
    for i in range(20):
        c.execute("INSERT INTO logs (timestamp, dht22_air_temp) VALUES (?, ?)", (f'2023-01-01 12:00:{i:02d}', 25.0))
    # Insert 20 relay log entries
    for i in range(20):
        c.execute("INSERT INTO relay_log (timestamp, relay_name, action) VALUES (?, ?, ?)", (f'2023-01-01 12:00:{i:02d}', 'RELAY1', 'ON'))
    conn.commit()
    conn.close()

    # Yield control to the test function
    yield

    # Teardown: remove the temporary database file
    os.unlink(db_path)

def test_get_logs_unlimited(temp_db):
    """Verify that get_logs with limit=0 or limit=None returns all records."""
    logs_zero = get_logs(limit=0)
    assert len(logs_zero) == 20

    logs_none = get_logs(limit=None)
    assert len(logs_none) == 20

def test_get_relay_log_unlimited(temp_db):
    """Verify that get_relay_log with limit=0 or limit=None returns all records."""
    relay_logs_zero = get_relay_log(limit=0)
    assert len(relay_logs_zero) == 20

    relay_logs_none = get_relay_log(limit=None)
    assert len(relay_logs_none) == 20

def test_get_logs_limited(temp_db):
    """Verify that get_logs with a specific limit returns the correct number of records."""
    logs = get_logs(limit=5)
    assert len(logs) == 5

def test_get_relay_log_limited(temp_db):
    """Verify that get_relay_log with a specific limit returns the correct number of records."""
    relay_logs = get_relay_log(limit=5)
    assert len(relay_logs) == 5
