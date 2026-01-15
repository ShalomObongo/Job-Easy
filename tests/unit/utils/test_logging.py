"""Tests for logging utility."""

import logging
from io import StringIO


class TestLoggerConfiguration:
    """Test that logger configures correctly from settings."""

    def test_configure_logging_creates_logger(self):
        """configure_logging should return a configured logger."""
        from src.utils.logging import configure_logging

        logger = configure_logging()
        assert isinstance(logger, logging.Logger)
        assert logger.name == "job_easy"

    def test_configure_logging_respects_level(self):
        """Logger should respect the configured log level."""
        from src.utils.logging import configure_logging

        logger = configure_logging(level="DEBUG")
        assert logger.level == logging.DEBUG

        logger = configure_logging(level="WARNING")
        assert logger.level == logging.WARNING

    def test_configure_logging_default_level_is_info(self):
        """Default log level should be INFO."""
        from src.utils.logging import configure_logging

        logger = configure_logging()
        assert logger.level == logging.INFO


class TestLogOutput:
    """Test that log output format is correct."""

    def test_log_message_includes_level(self):
        """Log messages should include the log level."""
        from src.utils.logging import configure_logging

        # Create a logger with a stream handler to stdout
        logger = configure_logging(level="INFO")

        # Add a handler that writes to a string buffer
        buffer = StringIO()
        handler = logging.StreamHandler(buffer)
        handler.setFormatter(logger.handlers[0].formatter)
        logger.addHandler(handler)

        logger.info("Test message")

        output = buffer.getvalue()
        assert "INFO" in output
        assert "Test message" in output

    def test_log_message_includes_timestamp(self):
        """Log messages should include a timestamp."""
        from src.utils.logging import configure_logging

        logger = configure_logging(level="INFO")

        buffer = StringIO()
        handler = logging.StreamHandler(buffer)
        handler.setFormatter(logger.handlers[0].formatter)
        logger.addHandler(handler)

        logger.info("Test message")

        output = buffer.getvalue()
        # Timestamp format includes date separators
        assert "-" in output or ":" in output


class TestGetLogger:
    """Test the get_logger convenience function."""

    def test_get_logger_returns_child_logger(self):
        """get_logger should return a child of the main logger."""
        from src.utils.logging import configure_logging, get_logger

        # Ensure main logger is configured
        configure_logging()

        logger = get_logger("my_module")
        assert logger.name == "job_easy.my_module"

    def test_get_logger_inherits_level(self):
        """Child logger should inherit parent's level."""
        from src.utils.logging import configure_logging, get_logger

        configure_logging(level="DEBUG")

        logger = get_logger("test_module")
        # Child loggers inherit effective level from parent
        assert logger.getEffectiveLevel() == logging.DEBUG
