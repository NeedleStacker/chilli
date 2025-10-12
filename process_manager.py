"""Small utility to manage long-running subprocesses (logger.py).

Provides a thread-safe ProcessManager class and convenience functions for the
project's single logger subprocess.
"""
import threading
import subprocess
import time
import os

class ProcessManager:
    def __init__(self, cmd, cwd=None, logfile=None):
        self.cmd = cmd
        self.cwd = cwd
        self.logfile = logfile
        self._lock = threading.Lock()
        self._proc = None

    def is_running(self):
        if self._proc and self._proc.poll() is None:
            return True
        self._proc = None
        return False

    def start(self):
        with self._lock:
            if self.is_running():
                return False, "Process already running."

            if self.logfile:
                logfile_dir = os.path.dirname(self.logfile)
                if logfile_dir:
                    os.makedirs(logfile_dir, exist_ok=True)
                logfile = open(self.logfile, "a")
            else:
                logfile = subprocess.DEVNULL

            try:
                proc = subprocess.Popen(self.cmd, cwd=self.cwd, stdout=logfile, stderr=subprocess.STDOUT)
            except Exception as e:
                return False, f"Failed to start process: {e}"

            self._proc = proc
            # Give process a moment to start
            time.sleep(0.5)
            if self.is_running():
                return True, f"Started (PID: {proc.pid})."
            else:
                return False, "Process did not stay running."

    def stop(self, timeout=5):
        with self._lock:
            if not self.is_running():
                return False, "Process not running."

            pid = self._proc.pid
            try:
                self._proc.terminate()
                self._proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self._proc.kill()

            self._proc = None
            return True, f"Stopped (PID: {pid})."


# --- Convenience helpers for the project logger ---
_logger_mgr = None

def init_logger_manager(base_dir, logger_script_name="logger.py", logger_logfile="logger_run.log"):
    global _logger_mgr
    script_path = os.path.join(base_dir, logger_script_name)
    cmd = ["python3", script_path, "run"]
    logfile = os.path.join(base_dir, logger_logfile)
    _logger_mgr = ProcessManager(cmd, cwd=base_dir, logfile=logfile)
    return _logger_mgr

def get_logger_manager():
    return _logger_mgr
