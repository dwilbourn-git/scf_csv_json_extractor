"""
Logging configuration for the SCF data pipeline.

This module sets up a consistent logging format and handlers for all pipeline components.
"""

import logging
import sys
from pathlib import Path


def setup_logging(verbose: bool = False, log_file: Path = None) -> logging.Logger:
    """
    Configure logging for the application.

    Args:
        verbose: If True, set log level to DEBUG. Otherwise, use INFO.
        log_file: Optional path to write logs to a file.

    Returns:
        Configured logger instance.
    """
    level = logging.DEBUG if verbose else logging.INFO

    # Create formatter
    formatter = logging.Formatter(
        fmt='%(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()  # Remove any existing handlers
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Name of the logger (typically __name__ from calling module).

    Returns:
        Logger instance.
    """
    return logging.getLogger(name)
