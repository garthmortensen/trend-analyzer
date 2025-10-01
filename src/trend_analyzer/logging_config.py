#!/usr/bin/env python3
#
# === FILE META OPENING ===
# file: ./trend-analyzer/src/trend_analyzer/logging_config.py
# role: logging
# desc: centralized logging configuration with timestamped files and stdout/stderr
# === FILE META CLOSING ===

import logging
import sys
from datetime import datetime
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
        """Setup logging with timestamped file and console output"""
        # Create logs directory
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file_path = logs_dir / f"{timestamp}.log"
        
        # Create logger
        self.logger = logging.getLogger("trend_analyzer")
        self.logger.setLevel(self.log_level)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        
        # File handler (detailed logs)
        file_handler = logging.FileHandler(self.log_file_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(file_handler)
        
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
        self.logger.info(f"Logging initialized - file: {self.log_file_path}")
    
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
        self.logger.debug(f"{config_name}_JSON: {json.dumps(config_data, indent=2, default=str)}")
        self.logger.info(f"=== END {config_name.upper()} CONFIGURATION ===")
    
    def info(self, message):
        """Log info message"""
        self.logger.info(message)
    
    def debug(self, message):
        """Log debug message"""
        self.logger.debug(message)
    
    def warning(self, message):
        """Log warning message"""
        self.logger.warning(message)
    
    def error(self, message):
        """Log error message"""
        self.logger.error(message)
    
    def critical(self, message):
        """Log critical message"""
        self.logger.critical(message)


# Global logger instance
logger = TrendAnalyzerLogger()

# Convenience functions
def log_config(config_name, config_data):
    """Log configuration data"""
    logger.log_config(config_name, config_data)

def info(message):
    """Log info message"""
    logger.info(message)

def debug(message):
    """Log debug message"""
    logger.debug(message)

def warning(message):
    """Log warning message"""
    logger.warning(message)

def error(message):
    """Log error message"""
    logger.error(message)

def critical(message):
    """Log critical message"""
    logger.critical(message)