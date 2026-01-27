"""Pytest configuration and fixtures for Trigger tests."""
import os
import pytest


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
