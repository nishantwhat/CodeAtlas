"""Structured logging configuration for program_graph."""

import logging
import sys


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure structured console logger."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger = logging.getLogger("program_graph")
    logger.setLevel(numeric_level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger