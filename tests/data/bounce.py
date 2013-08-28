# -*- coding: utf-8 -*-

"""
This file controls when bounce windows get auto-applied to network devices.

This module is expected to provide a ``bounce()`` function that takes a
`~trigger.netdevice.NetDevice` as the mandatory first argument and returns a
`~trigger.changemgmt.BounceWindow` object. The ``bounce()`` function is
imported by `~trigger.changemgmt` and `~trigger.netdevices`.

This file should be placed in the location specified in Trigger's
``settings.py`` using the :setting:`BOUNCE_FILE`` setting, which defaults to
``/etc/trigger/bounce.py``.

How you decide to return the bounce window object is up to you, and therein
lies the fun! This is meant to be an example of how one might customize bounce
windows and map them to devices in their environment.
"""

from trigger.changemgmt import BounceWindow as BW

# Bounce windows for Backbone (all times US/Eastern)
BACKBONE = {
    'ABC': BW(green='0, 22-23', yellow='1-12, 19-21', red='13-18'),
    'BBQ': BW(green='3-5', yellow='0-2, 6-11', red='12-23'),
    'COW': BW(green='5-7', yellow='1-4, 8-18', red='0, 19-23'),
    'FAP': BW(green='21-23', yellow='0-12, 19-20', red='13-18'),
    'FUN': BW(green='2-4', yellow='0-1, 5-14, 21-23', red='15-20'),
    'OMG': BW(green='5-7', yellow='1-4, 8-18', red='0, 19-23'),
    'XYZ': BW(green='3-5', yellow='0-2, 6-11', red='12-23'),
}

# Bounce windows for Data Center (all times US/Eastern)
DATACENTER = {
    'ABC': BW(green='5-7', yellow='0-4, 8-15', red='16-23'),
    'BBQ': BW(green='5-7', yellow='0-4, 8-15', red='16-23'),
    'FUN': BW(green='21-23', yellow='0-12, 17-20', red='13-16'),
    'OMG': BW(green='15-18', yellow='0-4, 19-23', red='5-14'),
    'XYZ': BW(green='5-7', yellow='0-4, 8-15', red='16-23'),
}

# Out-of-band network (all times US/Eastern)
OOB = {
    'ABC': BW(green='14-17', yellow='5-13, 18-20', red='1-4, 21-23'),
    'BBQ': BW(green='14-17', yellow='18-20', red='1-13, 21-23'),
    'OMG': BW(green='14-17', yellow='5-13, 18-20', red='1-4, 21-23'),
    'XYZ': BW(green='14-17', yellow='5-13, 18-20', red='1-4, 21-23'),
}

# Team definitions
TEAM_DC = 'Data Center'
TEAM_BB = 'Backbone'

# Mapping of team name to bounce windows
BOUNCE_MAP = {
    TEAM_DC: DATACENTER,
    TEAM_BB: BACKBONE,
}

# Defaults
DEFAULT_BOUNCE_SITE = 'ABC'
DEFAULT_BOUNCE_TEAM = TEAM_DC
DEFAULT_BOUNCE = BOUNCE_MAP[DEFAULT_BOUNCE_TEAM][DEFAULT_BOUNCE_SITE]

def bounce(device, default=DEFAULT_BOUNCE):
    """
    Return the bounce window for a given device.

    :param device:
        A `~trigger.netdevices.NetDevice` object.

    :param default:
        A `~trigger.changemgmt.BounceWindow` object.
    """

    # First try OOB, since it's special
    if 'ilo' in device.nodeName or 'oob' in device.nodeName:
        windows = OOB
    # Try to get the bounce windows by owningTeam
    else:
        windows = BOUNCE_MAP.get(device.owningTeam)

    # If we got nothin', return default
    if windows is None:
        return default

    # Try to get the bounce window by site, or fallback to default
    mybounce = windows.get(device.site, default)

    return mybounce
