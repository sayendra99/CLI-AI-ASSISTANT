"""Logging Configurations and Utilities."""

import logging
from pathlib import Path
from rich.logging import RichHandler
from Rocket.Utils.Config import settings


def setup_logger(name: str = "rocket", level: int = logging.INFO) -> logging.Logger:
    """Sets up a logger with a RichHandler and a file handler.

    - Creates a `rocket.log` file inside `settings.data_dir`.
    - Uses `RichHandler` for console formatting and a standard file handler for persisted logs.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicate logs
    logger.handlers.clear()

    console_handler = RichHandler(rich_tracebacks=True, markup=True, show_time=False, show_path=False)
    console_handler.setLevel(level)

    # File handler for output
    log_file_path = settings.data_dir / "rocket.log"
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def get_logger(name: str = "rocket") -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return setup_logger(name)


logger = setup_logger()