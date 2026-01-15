"""Logging configuration for Job-Easy."""

import logging
import sys

# Logger name for the application
LOGGER_NAME = "job_easy"

# Default log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Track if logging has been configured
_configured = False


def configure_logging(
    level: str | None = None,
    format_string: str = LOG_FORMAT,
    date_format: str = DATE_FORMAT,
) -> logging.Logger:
    """Configure and return the main application logger.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Defaults to INFO if not specified.
        format_string: Format string for log messages.
        date_format: Format string for timestamps.

    Returns:
        The configured root application logger.
    """
    global _configured

    # Get the main logger
    logger = logging.getLogger(LOGGER_NAME)

    # Determine log level
    if level is None:
        level = "INFO"
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Set the level
    logger.setLevel(log_level)

    # Only add handlers if not already configured
    if not _configured:
        # Remove any existing handlers
        logger.handlers.clear()

        # Create formatter
        formatter = logging.Formatter(format_string, datefmt=date_format)

        # Create console handler
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)

        # Add handler to logger
        logger.addHandler(console_handler)

        # Prevent propagation to root logger
        logger.propagate = False

        _configured = True
    else:
        # Update existing handler levels
        for handler in logger.handlers:
            handler.setLevel(log_level)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger for a specific module.

    Args:
        name: The module name (will be prefixed with 'job_easy.').

    Returns:
        A child logger for the module.
    """
    return logging.getLogger(f"{LOGGER_NAME}.{name}")


def reset_logging() -> None:
    """Reset logging configuration (useful for testing)."""
    global _configured

    logger = logging.getLogger(LOGGER_NAME)
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)

    _configured = False
