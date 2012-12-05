# -*- coding: utf-8 -*-

"""
This module controls how bounce windows get auto-applied to network devices.

This is primarily used by `~trigger.changemgmt`.

No changes should be made to this module. You must specify the path to the
bounce logic inside of ``settings.py`` as :setting:`BOUNCE_FILE`. This will be
exported as ``bounce()`` so that the module path for the :func:`bounce()`
function will still be `~trigger.changemgmt.bounce`.

This trickery allows us to keep the business-logic for how bounce windows are
mapped to devices out of the Trigger packaging.

If you do not specify a location for :setting:`BOUNCE_FILE`` or the module
cannot be loaded, then a default :func:`bounce()` function ill be used.
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2012, AOL Inc.'
__version__ = '0.1'


# Imports
from trigger.conf import settings
from trigger.utils.importlib import import_module_from_path
import warnings


# Exports
__all__ = ('bounce',)


# Load ``bounce()`` from the location of ``bounce.py``
bounce_mpath = settings.BOUNCE_FILE
try:
    _bounce_module = import_module_from_path(bounce_mpath, '_bounce_module')
    from _bounce_module import bounce
except ImportError:
    msg = 'Bounce mappings could not be found in %s. using default!' % bounce_mpath
    warnings.warn(msg, RuntimeWarning)
    from . import BounceWindow
    DEFAULT_BOUNCE = BounceWindow(green='5-7', yellow='0-4, 8-15', red='16-23')
    def bounce(device, default=DEFAULT_BOUNCE):
        """
        Return the bounce window for a given device.

        :param device:
            A `~trigger.netdevices.NetDevice` object.

        :param default:
            A `~trigger.changemgmt.BounceWindow` object.
        """
        return default
