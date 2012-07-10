# -*- coding: utf-8 -*-

"""
Trigger's ACL parser.

This library contains various modules that allow for parsing, manipulation,
and management of network access control lists (ACLs). It will parse a complete
ACL and return an ACL object that can be easily translated to any supported
vendor syntax.
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2010-2012, AOL Inc.'

import os
from trigger.conf import settings
from trigger.acl.parser import *

__all__ = ['acl_exists', 'parse', 'ACL']
#__all__.extend(list(parser.__all__)) # Include parser.__all__ (duh!)


# Functions
def acl_exists(name):
    return os.access(settings.FIREWALL_DIR + '/acl.' + name, os.R_OK)

