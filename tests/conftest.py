"""Pytest configuration and fixtures for Trigger tests."""
import os
import sys
import pytest


# Add project root to Python path (replaces pytest-pythonpath)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up required environment variables for all tests."""
    test_data_dir = os.path.join(os.path.dirname(__file__), "data")

    os.environ["TRIGGER_SETTINGS"] = os.path.join(test_data_dir, "settings.py")
    os.environ["NETDEVICES_SOURCE"] = os.path.join(test_data_dir, "netdevices.xml")
    os.environ["AUTOACL_FILE"] = os.path.join(test_data_dir, "autoacl.py")
    os.environ["BOUNCE_FILE"] = os.path.join(test_data_dir, "bounce.py")
    os.environ["TACACSRC"] = os.path.join(test_data_dir, "tacacsrc")
    os.environ["TACACSRC_KEYFILE"] = os.path.join(test_data_dir, "tackf")
