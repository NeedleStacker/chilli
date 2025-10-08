import os
import pytest
from webserver import is_logger_running
from config import PID_FILE

# Fixture to manage the PID file for tests
@pytest.fixture
def manage_pid_file():
    # Setup: ensure the PID file does not exist before the test
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

    yield # This is where the test runs

    # Teardown: clean up the PID file after the test
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

def test_is_logger_running_when_not_running(manage_pid_file):
    """
    Test that is_logger_running returns False when the PID file doesn't exist.
    """
    assert not is_logger_running()

def test_is_logger_running_with_stale_pid_file(manage_pid_file):
    """
    Test that is_logger_running returns False and cleans up a stale PID file.
    A stale PID file is one that contains a PID of a non-existent process.
    """
    # Create a fake PID file with a non-existent PID
    with open(PID_FILE, "w") as f:
        f.write("99999") # A very unlikely to exist PID

    assert not is_logger_running()
    # The function should also remove the stale PID file
    assert not os.path.exists(PID_FILE)

def test_is_logger_running_when_running(manage_pid_file):
    """
    Test that is_logger_running returns True when the logger is running.
    This is simulated by creating a PID file with the current process's PID.
    """
    # Create a PID file with the current process's PID
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    assert is_logger_running()
    # The function should not remove a valid PID file
    assert os.path.exists(PID_FILE)