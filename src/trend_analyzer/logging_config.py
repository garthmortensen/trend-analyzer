#!/usr/bin/env python3
#
# === FILE META OPENING ===
# file: ./trend-analyzer/src/trend_analyzer/logging_config.py
# role: logging
# desc: centralized logging configuration with timestamped files and stdout/stderr
# === FILE META CLOSING ===

import logging
import sys
from pathlib import Path
import json


class TrendAnalyzerLogger:
    """Centralized logger for trend analyzer with file and console output"""

    def __init__(self, log_level=logging.INFO):
        self.log_level = log_level
        self.logger = None
        self.log_file_path = None
        self._setup_logging()

    def _setup_logging(self):
        """Setup logging with console output only (file logging disabled)"""
        # Create logger
        self.logger = logging.getLogger("trend_analyzer")
        self.logger.setLevel(self.log_level)

        # Clear any existing handlers
        self.logger.handlers.clear()

        # Create formatters
        console_formatter = logging.Formatter("%(levelname)s: %(message)s")

        # Console handler for INFO and above (stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # Error handler for ERROR and above (stderr)
        error_handler = logging.StreamHandler(sys.stderr)
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(console_formatter)
        self.logger.addHandler(error_handler)

        # Log initial setup
        self.logger.info("Logging initialized - console only")

    def log_config(self, config_name, config_data):
        """Log configuration data in a structured format"""
        self.logger.info(f"=== {config_name.upper()} CONFIGURATION ===")

        if isinstance(config_data, dict):
            for key, value in config_data.items():
                if isinstance(value, dict):
                    self.logger.info(f"{key}:")
                    for sub_key, sub_value in value.items():
                        self.logger.info(f"  {sub_key}: {sub_value}")
                else:
                    self.logger.info(f"{key}: {value}")
        else:
            self.logger.info(f"{config_name}: {config_data}")

        # Also log as JSON for parsing
        self.logger.debug(
            f"{config_name}_JSON: {json.dumps(config_data, indent=2, default=str)}"
        )
        self.logger.info(f"=== END {config_name.upper()} CONFIGURATION ===")

    def info(self, message, **kwargs):
        """Log info message"""
        self.logger.info(message, **kwargs)

    def debug(self, message, **kwargs):
        """Log debug message"""
        self.logger.debug(message, **kwargs)

    def warning(self, message, **kwargs):
        """Log warning message"""
        self.logger.warning(message, **kwargs)

    def error(self, message, **kwargs):
        """Log error message"""
        self.logger.error(message, **kwargs)

    def critical(self, message, **kwargs):
        """Log critical message"""
        self.logger.critical(message, **kwargs)

    def reconfigure_log_file(self, new_log_path):
        """Reconfigure logger to write to a new file location (e.g., run directory)"""
        new_log_path = Path(new_log_path)
        
        # Remove existing file handlers
        for handler in self.logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                handler.close()
                self.logger.removeHandler(handler)
        
        # Create new file handler
        detailed_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        
        file_handler = logging.FileHandler(new_log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(file_handler)
        
        self.log_file_path = new_log_path
        self.logger.info(f"Log file relocated to: {new_log_path}")


# Global logger instance
logger = TrendAnalyzerLogger()


# Convenience functions
def log_config(config_name, config_data):
    """Log configuration data"""
    logger.log_config(config_name, config_data)


def info(message, **kwargs):
    """Log info message"""
    logger.info(message, **kwargs)


def debug(message, **kwargs):
    """Log debug message"""
    logger.debug(message, **kwargs)


def warning(message, **kwargs):
    """Log warning message"""
    logger.warning(message, **kwargs)


def error(message, **kwargs):
    """Log error message"""
    logger.error(message, **kwargs)


def critical(message, **kwargs):
    """Log critical message"""
    logger.critical(message, **kwargs)


def reconfigure_log_file(new_log_path):
    """Reconfigure logger to write to new file location"""
    logger.reconfigure_log_file(new_log_path)
