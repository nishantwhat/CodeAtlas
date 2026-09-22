"""Milestone 0 environment verification tests."""

import sys
import pytest
from program_graph.application.config import load_config
from program_graph.application.logging import setup_logging
import logging

def test_python_version():
    """Verify runtime Python version is 3.11+."""
    assert sys.version_info >= (3, 11), "Python 3.11+ required"


def test_config_loading():
    """Verify application configuration loading."""
    config = load_config()
    assert config.env == "development"
    assert config.analysis.default_c_standard == "c11"


def test_logging_initialization():
    """Verify structured logger initialization."""
    logger = setup_logging("DEBUG")
    assert logger.level == logging.DEBUG