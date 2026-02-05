"""Pytest configuration and fixtures for Trigger tests."""

import os
import sys
from pathlib import Path

# Add project root to Python path (replaces pytest-pythonpath)
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# Set up environment variables BEFORE any trigger imports
# This must happen at module level, not in a fixture, because trigger modules
# import and read these settings at import time
test_data_dir = Path(__file__).parent / "data"
os.environ["TRIGGER_SETTINGS"] = str(test_data_dir / "settings.py")
os.environ["NETDEVICES_SOURCE"] = str(test_data_dir / "netdevices.xml")
os.environ["AUTOACL_FILE"] = str(test_data_dir / "autoacl.py")
os.environ["BOUNCE_FILE"] = str(test_data_dir / "bounce.py")
os.environ["TACACSRC"] = str(test_data_dir / "tacacsrc")
os.environ["TACACSRC_KEYFILE"] = str(test_data_dir / "tackf")
