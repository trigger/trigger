# -*- coding: utf-8 -*-

"""
Abstract interface to bounce windows and moratoria.
"""

__author__ = 'Jathan McCollum, Mark Thomas, Michael Shields'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2006-2012, AOL Inc.'

# Imports
from datetime import datetime, timedelta
from pytz import timezone, UTC
from trigger.conf import settings
from trigger import exceptions


# Constants
BOUNCE_VALUES = ('green', 'yellow', 'red')
BOUNCE_DEFAULT_TZ = timezone(settings.BOUNCE_DEFAULT_TZ)
BOUNCE_DEFAULT_COLOR = settings.BOUNCE_DEFAULT_COLOR
BOUNCE_VALUE_MAP = {
    'red': 3,
    'yellow': 2,
    'green': 1,
}


# Exports
__all__ = ('BounceStatus', 'BounceWindow', 'bounce')


# Classes
class BounceStatus(object):
    """
    An object that represents a bounce window risk-level status.

    + green: Low risk
    + yellow: Medium risk
    + red: High risk

    Objects stringify to 'red', 'green', or 'yellow', and can be compared
    against those strings. Objects can also be compared against each other.
    'red' > 'yellow' > 'green'.

        >>> green = BounceStatus('green')
        >>> yellow = BounceStatus('yellow')
        >>> print green
        green
        >>> yellow > green
        True

    :param status_name:
        The colored risk-level status name.
    """
    def __init__(self, status_name):
        self.status_name = status_name
        self.value = BOUNCE_VALUES.index(status_name)

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.status_name)

    def __str__(self):
        return self.status_name

    def __cmp__(self, other):
        try:
            return self.value.__cmp__(other.value)
        except AttributeError:
            # Other object is not a BounceStatus; maybe it's a string.
            return self.value.__cmp__(BounceStatus(other).value)

class BounceWindow(object):
    """
    Build a bounce window of 24 `~trigger.changemgmt.BounceStatus` objects.

    You may either specify your own list of 24
    `~trigger.changemgmt.BounceStatus` objects using ``status_by_hour``, or you
    may omit this argument and specify your  'green', 'yellow', and 'red'
    risk levels by using hyphenated and comma-separated text strings.

    You may use digits ("14") or hyphenated ranges ("0-5") and may join these
    together using a comma (",") with or without spacing separating them. For
    example "0-5, 14" will be parsed into ``[0, 1, 2, 3, 4, 5, 14]``.

    The `default` color is used to fill in the gaps  between the other colors,
    so that the total is always 24 in the resultant list status objects.

        >>> b = BounceWindow(green='0-3, 23', red='10', default='yellow')
        >>> b.status()
        <BounceStatus: yellow>
        >>> b.next_ok('green')
        datetime.datetime(2012, 12, 5, 4, 0, tzinfo=<UTC>)
        >>> b.dump()
        {0: <BounceStatus: green>,
         1: <BounceStatus: green>,
         2: <BounceStatus: green>,
         3: <BounceStatus: green>,
         4: <BounceStatus: yellow>,
         5: <BounceStatus: yellow>,
         6: <BounceStatus: yellow>,
         7: <BounceStatus: yellow>,
         8: <BounceStatus: yellow>,
         9: <BounceStatus: yellow>,
         10: <BounceStatus: red>,
         11: <BounceStatus: yellow>,
         12: <BounceStatus: yellow>,
         13: <BounceStatus: yellow>,
         14: <BounceStatus: yellow>,
         15: <BounceStatus: yellow>,
         16: <BounceStatus: yellow>,
         17: <BounceStatus: yellow>,
         18: <BounceStatus: yellow>,
         19: <BounceStatus: yellow>,
         20: <BounceStatus: yellow>,
         21: <BounceStatus: yellow>,
         22: <BounceStatus: yellow>,
         23: <BounceStatus: green>}

    You may modify the global default fallback color by setting
    :setting:`BOUNCE_DEFAULT_COLOR` in your ``settings.py``.

    Although the query API is generic and could accomodate any sort of bounce
    window policy, this constructor knows only about AOL's bounce windows,
    which operate on "US/Eastern" time (worldwide), always change on hour
    boundaries, and are the same every day. If that ever changes, only this
    class will need to be updated.

    End-users are not expected to create new ``BounceWindow`` objects;
    instead, use `~trigger.changemgmt.bounce()` or
    `~trigger.netdevices.NetDevice.bounce` to get an object,
    then query its methods.

    :param status_by_hour:
        (Optional) A list of 24 `~trigger.changemgmt.BounceStatus` objects.

    :param green:
        Representative string of hours.

    :param yellow:
        Representative string of hours.

    :param red:
        Representative string of hours.

    :param default:
        The color used to fill in the gaps between other risk levels.
    """
    # Prepopulate these objects to save a little horsepower
    BOUNCE_STATUS = dict([(n, BounceStatus(n)) for n in BOUNCE_VALUES])

    def __init__(self, status_by_hour=None, green=None, yellow=None, red=None,
                 default=BOUNCE_DEFAULT_COLOR):

        # Parse the hours specified into BounceWindows
        self._green = green
        self._yellow = yellow
        self._red = red
        self.default = default
        hours = {
            'green': self._parse_hours(green),
            'yellow':  self._parse_hours(yellow),
            'red':  self._parse_hours(red),
        }
        self.hours = hours
        self.hour_map = self._map_bounces(self.hours, default=default)

        # Allow for providing status_by_hour, but don't rely on it
        if status_by_hour is None:
            status_by_hour = self.hour_map.values()

        if not len(status_by_hour) == 24:
            msg = 'There must be exactly 24 hours defined for this BounceWindow.'
            raise exceptions.InvalidBounceWindow(msg)

        # Make sure each status occurs at least once, or next_ok()
        # might never return.
        for status in BOUNCE_VALUE_MAP:
            if status not in status_by_hour:
                msg = '%s risk-level must be defined!' % status
                raise exceptions.InvalidBounceWindow(msg)
        self._status_by_hour = status_by_hour

    def __repr__(self):
        return "%s(green=%r, yellow=%r, red=%r, default=%r)" % (self.__class__.__name__,
                                                                self._green,
                                                                self._yellow,
                                                                self._red,
                                                                self.default)

    def status(self, when=None):
        """
        Return a `~trigger.changemgmt.BounceStatus` object for the specified
        time or now.

        :param when:
            A ``datetime`` object.
        """
        when_et = (when or datetime.now(tz=UTC)).astimezone(BOUNCE_DEFAULT_TZ)

        # Return default during weekend moratorium, otherwise look it up.
        if (when_et.weekday() >= 5 or
            when_et.weekday() == 0 and when_et.hour < 4 or
            when_et.weekday() == 4 and when_et.hour >= 12):
            return BounceStatus(BOUNCE_DEFAULT_COLOR)
        else:
            return self._status_by_hour[when_et.hour]

    def next_ok(self, status, when=None):
        """
        Return the next time at or after the specified time (default now) that
        it the bounce status will be at equal to or less than the given status.

        For example, ``next_ok('yellow')`` will return the time that the bounce
        window becomes 'yellow' or 'green'. Returns UTC time.

        :param status:
            The colored risk-level status name.

        :param when:
            A ``datetime`` object.
        """
        when = when or datetime.now(tz=UTC)
        if self.status(when) <= status:
            return when.astimezone(UTC)
        when = datetime(when.year, when.month, when.day, when.hour, tzinfo=UTC)
        when += timedelta(hours=1)
        while self.status(when) > status:
            when += timedelta(hours=1)
        return when

    def dump(self):
        """Dump a mapping of hour to status"""
        return self.hour_map

    def _get_bounces(self, hours, color):
        """
        Return a list of hours mapped to bounce objects

        :param hours:
            A list of integers representing hours

        :param color:
            The risk-level color name.
        """
        return zip(hours, [self.BOUNCE_STATUS[color]] * len(hours))

    def _map_bounces(self, hdict, default=None):
        """
        Map a dictionary of colors and hours into a dictionary keyed by hour and
        the appropriate BounceStatus object.

        :param hdict:
            Dictionary mapping of hours to status objects.

        :param default:
            The default bounce status name.
        """
        if default is None:
            default = self.default
        status = []
        for color, hours in hdict.iteritems():
            status.extend(self._get_bounces(hours, color))

        # Fill in missing keys with the default color
        missing = [i for i in range(24) if i not in dict(status)]
        if missing:
            status.extend(self._get_bounces(missing, default))

        return dict(status)

    def _parse_hours(self, hs):
        """
        Parse hour strings into lists of hours. Or if a list of hours is passed
        in, just return it as is.

        >>> parse_hours('0-3, 23')
        [0, 1, 2, 3, 23]
        parse_hours(range(3))
        [0, 1, 2]

        :param hs:
            A string representation of hours.
        """
        myhours = []
        if hs is None:
            return myhours

        # Assume it's a list of integers?
        if isinstance(hs, list):
            return hs

        # Split the pattern by ',' and then trim whitespace, carve hyphenated
        # ranges out and then return a list of hours. More error-checking
        # Coming "Soon".
        blocks = hs.split(',')
        for block in blocks:
            # Clean whitespace and split on hyphens
            parts = block.strip().split('-')
            parts = [int(p) for p in parts] # make ints
            if len(parts) == 1: # no hyphen
                parts.append(parts[0] + 1)
            elif len(parts) == 2:
                parts[1] += 1
            else:
                raise RuntimeError("This should not have happened!")

            # Return the individual hours
            for i in range(*parts):
                myhours.append(i)

        return myhours


# Load ``bounce()`` from the location of ``bounce.py`` or provide a dummy that
# returns a hard-coded bounce window
from .bounce import bounce
