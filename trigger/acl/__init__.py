"""Trigger's ACL parser.

This library contains various modules that allow for parsing, manipulation,
and management of network access control lists (ACLs). It will parse a complete
ACL and return an ACL object that can be easily translated to any supported
vendor syntax.
"""

import os

from trigger.conf import settings

__all__ = ["acl_exists", "parser"]

# Parser
from . import parser
from .parser import *  # noqa: F403

__all__.extend(parser.__all__)


# Functions
def acl_exists(name):  # noqa: D103
    return os.access(settings.FIREWALL_DIR + "/acl." + name, os.R_OK)
