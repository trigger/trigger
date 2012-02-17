"""
Settings and configuration for Trigger. Attempts to load from 
``SETTINGS_FILE`` and complains if it can't. The primary public interface
for this module is the ``settings`` variable, which is a module object
containing the variables found in ``trigger_settings.py``.

>>> from trigger.conf import settings
>>> settings.FIREWALL_DIR
'/data/firewalls'
>>> settings.REDIS_HOST
'127.0.0.1'
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2010-2011, AOL Inc.'

import os
import sys

# Defaults
SETTINGS_FILE = '/etc/trigger_settings.py'

# Exports
__all__ = ('settings', 'DummySettings', 'import_path')


# Functions
def import_path(full_path, global_name):
    """ 
    Import a file with full path specification. Allows one to
    import from anywhere, something ``__import__`` does not do. 

    Also adds the module to ``sys.modules`` as module_name

    :param full_path: The absolute path to the module .py file
    :param global_name: The name assigned to the module in sys.modules. To avoid
        confusion, the global_name should be the same as the variable to which
        you're assigning the returned module.

    Returns a module object.
    """
    path, filename = os.path.split(full_path)
    module, ext = os.path.splitext(filename)
    sys.path.append(path)

    try:
        mymodule = __import__(module)
        sys.modules[global_name] = mymodule
    except ImportError:
        print 'Settings module could not be imported, please make sure %s is correct.' % full_path
        raise
    finally:
        del sys.path[-1]

    return mymodule

# This is our settings object 
settings = import_path(SETTINGS_FILE, 'settings')

# Classes
class DummySettings(object):
    """Emulates settings and returns empty strings on attribute gets."""
    def __getattribute__(self, name):
        return ''
