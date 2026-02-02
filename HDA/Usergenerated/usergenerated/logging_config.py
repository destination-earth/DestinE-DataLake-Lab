import logging
import logging.config
from logging.handlers import RotatingFileHandler
from typing import Optional

from config import (
    APP_LOGGER_FILE_BACKUP_COUNT,
    APP_LOGGER_FILE_PATH,
    APP_LOGGER_FILE_TRUNCATE_SIZE,
    APP_LOGGER_LEVEL,
    APP_LOGGER_NAME,
)


def setup_logging(
    log_file_path: str = APP_LOGGER_FILE_PATH, level: int = logging.DEBUG
) -> None:
    """
    Set up logging configuration with different formatters for console and file handlers.

    Args:
        log_file_path: Path to the log file.
        level: Logging level (default: logging.DEBUG).
    """
    # Create a custom logger: same logger for all processes
    logger = logging.getLogger(APP_LOGGER_NAME)

    # Set the logging level
    logger.setLevel(level)

    # Create handlers
    console_handler = logging.StreamHandler()
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=APP_LOGGER_FILE_TRUNCATE_SIZE,
        backupCount=APP_LOGGER_FILE_BACKUP_COUNT,
    )

    # Set level for handlers
    console_handler.setLevel(level)
    file_handler.setLevel(level)

    # Create formatters
    console_formatter = logging.Formatter("%(message)s")
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Set formatters to handlers
    console_handler.setFormatter(console_formatter)
    file_handler.setFormatter(file_formatter)

    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


# Logging is setup if another file imports this module.
# import usergenerated.logging_config should only be done in e.g. generate_item_metadata before other module imports
setup_logging(APP_LOGGER_FILE_PATH, APP_LOGGER_LEVEL)
