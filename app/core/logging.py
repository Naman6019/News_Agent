"""
Logging configuration for AI News Agent
"""

import logging
import sys
from typing import Dict, Any

from app.core.config import settings


def setup_logging() -> None:
    """Configure application logging."""

    # Create formatter
    formatter = logging.Formatter(settings.LOG_FORMAT)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # File handler for persistent logs
    file_handler = logging.FileHandler("news_agent.log")
    file_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("feedparser").setLevel(logging.WARNING)
    logging.getLogger("twilio").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    return logging.getLogger(name)


class StructuredLogger:
    """Structured logging utility for better log management."""

    def __init__(self, logger_name: str):
        self.logger = get_logger(logger_name)

    def info(self, message: str, **kwargs: Dict[str, Any]) -> None:
        """Log info message with structured data."""
        if kwargs:
            message = f"{message} | {kwargs}"
        self.logger.info(message)

    def error(self, message: str, exc: Exception = None, **kwargs: Dict[str, Any]) -> None:
        """Log error message with structured data."""
        if exc:
            kwargs["exception"] = str(exc)
            kwargs["exception_type"] = type(exc).__name__
        if kwargs:
            message = f"{message} | {kwargs}"
        self.logger.error(message, exc_info=exc is not None)

    def warning(self, message: str, **kwargs: Dict[str, Any]) -> None:
        """Log warning message with structured data."""
        if kwargs:
            message = f"{message} | {kwargs}"
        self.logger.warning(message)

    def debug(self, message: str, **kwargs: Dict[str, Any]) -> None:
        """Log debug message with structured data."""
        if kwargs:
            message = f"{message} | {kwargs}"
        self.logger.debug(message)