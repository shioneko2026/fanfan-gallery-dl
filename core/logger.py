"""
System logger for GUI
Captures all logs and emits them to UI
"""
from PyQt6.QtCore import QObject, pyqtSignal
from datetime import datetime
from typing import Optional
import sys


class SystemLogger(QObject):
    """System logger that emits log messages to UI"""

    log_message = pyqtSignal(str, str)  # level, message

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Only initialize QObject once using class variable
        if not SystemLogger._initialized:
            super().__init__()
            SystemLogger._initialized = True

    def info(self, message: str):
        """Log info message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] INFO: {message}"
        print(log_line)
        self.log_message.emit("INFO", log_line)

    def success(self, message: str):
        """Log success message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] SUCCESS: {message}"
        print(log_line)
        self.log_message.emit("SUCCESS", log_line)

    def warning(self, message: str):
        """Log warning message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] WARNING: {message}"
        print(log_line)
        self.log_message.emit("WARNING", log_line)

    def error(self, message: str):
        """Log error message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] ERROR: {message}"
        print(log_line, file=sys.stderr)
        self.log_message.emit("ERROR", log_line)

    def debug(self, message: str):
        """Log debug message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] DEBUG: {message}"
        print(log_line)
        self.log_message.emit("DEBUG", log_line)


# Global logger instance (lazy initialization)
_logger_instance = None

def get_logger():
    """Get or create the logger instance"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = SystemLogger()
    return _logger_instance

# Expose logger as a module-level object for convenience
class _LoggerProxy:
    """Proxy that lazily creates the logger when accessed"""
    def __getattr__(self, name):
        return getattr(get_logger(), name)

logger = _LoggerProxy()
