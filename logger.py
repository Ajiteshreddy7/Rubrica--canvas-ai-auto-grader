"""
Logging configuration for the auto-grading daemon.

Provides file logging with rotation alongside Rich console output.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOGS_DIR = Path(__file__).parent / "logs"


def setup_logger(name: str = "autograder", level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger with rotating file handler.

    Logs are written to logs/autograder.log with rotation at 5MB, keeping 5 backups.
    """
    LOGS_DIR.mkdir(exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    # File handler with rotation
    file_handler = RotatingFileHandler(
        LOGS_DIR / "autograder.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# Module-level logger instance
log = setup_logger()
