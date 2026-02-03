"""Pytest configuration and fixtures for Trigger tests."""

import os
import sys

# Add project root to Python path (replaces pytest-pythonpath)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# Set up environment variables BEFORE any trigger imports
# This must happen at module level, not in a fixture, because trigger modules
# import and read these settings at import time
test_data_dir = os.path.join(os.path.dirname(__file__), "data")
os.environ["TRIGGER_SETTINGS"] = os.path.join(test_data_dir, "settings.py")
os.environ["NETDEVICES_SOURCE"] = os.path.join(test_data_dir, "netdevices.xml")
os.environ["AUTOACL_FILE"] = os.path.join(test_data_dir, "autoacl.py")
os.environ["BOUNCE_FILE"] = os.path.join(test_data_dir, "bounce.py")
os.environ["TACACSRC"] = os.path.join(test_data_dir, "tacacsrc")
os.environ["TACACSRC_KEYFILE"] = os.path.join(test_data_dir, "tackf")
