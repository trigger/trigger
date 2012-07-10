"""
Settings and configuration for Trigger.

Values will be read from the module specified by the ``TRIGGER_SETTINGS``
environment variable, and then from trigger.conf.global_settings; see the
global settings file for a list of all possible variables.

If ``TRIGGER_SETTINGS`` is not set, it will attempt to load from
``/etc/trigger/settings.py`` and complains if it can't. The primary public
interface for this module is the ``settings`` variable, which is a module
object containing the variables found in ``settings.py``.

>>> from trigger.conf import settings
>>> settings.FIREWALL_DIR
'/data/firewalls'
>>> settings.REDIS_HOST
'127.0.0.1'
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2010-2012, AOL Inc.'

import os
import sys
import warnings

from . import global_settings

# Defaults
DEFAULT_LOCATION = '/etc/trigger/settings.py'
ENVIRONMENT_VARIABLE = 'TRIGGER_SETTINGS'
SETTINGS_FILE = os.environ.get(ENVIRONMENT_VARIABLE, DEFAULT_LOCATION)


# Exports
__all__ = ('settings', 'DummySettings', 'import_path', 'BaseSettings',
           'Settings')


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
        raise ImportError('Module could not be imported from %s.' % full_path)
    finally:
        del sys.path[-1]

    return mymodule


# Classes
class DummySettings(object):
    """Emulates settings and returns empty strings on attribute gets."""
    def __getattribute__(self, name):
        return ''

# BaseSettings and Settings concepts were lifted from Django's objects of the
# same name, except our implementation is simplified. (See: django.conf.__init__.py)
class BaseSettings(object):
    """
    Common logic for settings whether set by a module or by the user.
    """
    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)

class Settings(BaseSettings):
    def __init__(self, settings_module):
        # Update this dict from global settings (but only for ALL_CAPS settings)
        for setting in dir(global_settings):
            if setting == setting.upper():
                setattr(self, setting, getattr(global_settings, setting))

        # Store the settings module in case someone later cares
        self.SETTINGS_MODULE = settings_module

        mod = import_path(settings_module, 'settings')

        # Settings that should be converted into tuples if they're mistakenly entered
        # as strings.
        tuple_settings = ("SUPPORTED_VENDORS", "IOSLIKE_VENDORS", "VALID_OWNERS")

        # Now override anything configured in the custom settings
        for setting in dir(mod):
            if setting == setting.upper():
                setting_value = getattr(mod, setting)
                if setting in tuple_settings and type(setting_value) == str:
                    setting_value = (setting_value,) # In case the user forgot the comma.
                setattr(self, setting, setting_value)

# This is our settings object
try:
    settings = Settings(SETTINGS_FILE)
except ImportError as err:
    # Complain loudly but carry on with defaults
    warnings.warn(str(err) + ' Using default global settings.', RuntimeWarning)
    settings = global_settings
