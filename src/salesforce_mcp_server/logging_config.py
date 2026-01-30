"""Centralized logging configuration for Salesforce MCP Server."""

import logging
import os


def get_logger(name: str) -> logging.Logger:
    """Get a module-specific logger.

    Args:
        name: Module name (will be prefixed with 'salesforce_mcp.')

    Returns:
        Configured logger instance
    """
    return logging.getLogger(f"salesforce_mcp.{name}")


def setup_logging() -> None:
    """Initialize logging configuration.

    Reads LOG_LEVEL from environment variables (default: INFO).
    Valid levels: DEBUG, INFO, WARNING, ERROR
    """
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Set the root logger for our package
    package_logger = logging.getLogger("salesforce_mcp")
    package_logger.setLevel(level)
