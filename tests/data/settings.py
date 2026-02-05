import os
from pathlib import Path

# Owners to use in testing...
VALID_OWNERS = ("Data Center",)

# Database stuff
DATABASE_ENGINE = "sqlite3"

# The prefix is... ME! (Abs path to the current file)
PREFIX = str(Path(__file__).resolve().parent)

# .tacacsrc Stuff
DEFAULT_REALM = "aol"
TACACSRC_KEYFILE = os.getenv("TACACSRC_KEYFILE", str(Path(PREFIX) / "tackf"))
TACACSRC = os.getenv("TACACSRC", str(Path(PREFIX) / "tacacsrc"))
RIGHT_TACACSRC = os.getenv("TACACSRC", str(Path(PREFIX) / "right_tacacsrc"))
MEDIUMPW_TACACSRC = os.getenv("TACACSRC", str(Path(PREFIX) / "mediumpw_tacacsrc"))
LONGPW_TACACSRC = os.getenv("TACACSRC", str(Path(PREFIX) / "longpw_tacacsrc"))
BROKENPW_TACACSRC = os.getenv("TACACSRC", str(Path(PREFIX) / "brokenpw_tacacsrc"))
EMPTYPW_TACACSRC = os.getenv("TACACSRC", str(Path(PREFIX) / "emptypw_tacacsrc"))

# Enable ACL support
WITH_ACLS = True

# Configs
NETDEVICES_SOURCE = os.environ.get(
    "NETDEVICES_SOURCE",
    str(Path(PREFIX) / "netdevices.xml"),
)
AUTOACL_FILE = os.environ.get("AUTOACL_FILE", str(Path(PREFIX) / "autoacl.py"))
BOUNCE_FILE = os.environ.get("BOUNCE_FILE", str(Path(PREFIX) / "bounce.py"))

TEXTFSM_TEMPLATE_DIR = os.getenv(
    "TEXTFSM_TEMPLATE_DIR",
    str(Path(PREFIX) / "vendor/ntc_templates"),
)
