# -*- coding: utf-8 -*-

"""Abstract interface to bounce windows and moratoria."""

__author__ = 'Jathan McCollum, Mark Thomas, Michael Shields'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2006-2011, AOL Inc.'

from datetime import datetime, timedelta
from pytz import timezone, UTC

# Defaults
DEFAULT_BOUNCE_TZ = timezone('US/Eastern')
DEFAULT_BOUNCE_SITE = 'DTC'
DEFAULT_BOUNCE_REALM = 'BBEN'
DEFAULT_BOUNCE_GROUP = (DEFAULT_BOUNCE_SITE, DEFAULT_BOUNCE_REALM)
DEFAULT_BOUNCE_COLOR = 'red'
BOUNCE_VALUE_MAP = {
    'red': 3,
    'yellow': 2,
    'green': 1,
}


# Classes
class BounceStatus(object):
    """
    Class for bounce window statuses.

    Objects stringify to 'red', 'green', or 'yellow', and can be compared
    against those strings.  Objects can also be compared against each other.
    'red' > 'yellow' > 'green'.
    """
    def __init__(self, status_name):
        self.status_name = status_name
        self.value = BOUNCE_VALUE_MAP[status_name]

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
    Build a bounce window based on a list of 24 BounceStatus objects.
        
    Although the query API is generic and could accomodate any sort of
    bounce window policy, this constructor knows only about AOL's bounce
    windows, which operate on US Eastern time (worldwide), always change
    on hour boundaries, and are the same every day.  If that ever changes,
    only this class will need to be updated.

    End-users are not expected to create new BounceWindow objects;
    instead, use site_bounce() or NetDevice.site.bounce to get an object,
    then query its methods.
    """
    def __init__(self, status_by_hour):
        assert len(status_by_hour) == 24
        # Make sure each status occurs at least once, or next_ok()
        # might never return.
        for status in BOUNCE_VALUE_MAP:
            assert status in status_by_hour
        self._status_by_hour = status_by_hour

    def __repr__(self):
        return "<%s: current status: %s>" % (self.__class__.__name__,
                                             str(self.status()))

    def status(self, when=None):
        """Return a BounceStatus object for the specified time, or for now."""
        when_et = (when or datetime.now(tz=UTC)).astimezone(DEFAULT_BOUNCE_TZ)

        # Return default during weekend moratorium, otherwise look it up.
        if (when_et.weekday() >= 5 or
            when_et.weekday() == 0 and when_et.hour < 4 or
            when_et.weekday() == 4 and when_et.hour >= 12):
            return BounceStatus(DEFAULT_BOUNCE_COLOR)
        else:
            return self._status_by_hour[when_et.hour]

    def next_ok(self, status, when=None):
        """
        Return the next time at or after the specified time (default now)
        that it the bounce status will be at equal to or less than the given status.
        For example, next_ok('yellow') will return the time that the bounce window
        becomes yellow or green.  Returns UTC time.
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
        return dict(enumerate(self._status_by_hour))

# Map owningTeam definitions to realm name (temporary)
REALM_MAP = {
    'AOL Transit Data Network': 'ATDN',
}

def lookup_realm(owning_team):
    """Given an owning team, return the mapped bounce realm"""
    return REALM_MAP.get(owning_team, DEFAULT_BOUNCE_REALM)

def site_bounce(site, owning_team=None):
    """Return the bounce window for the given site."""
    realm = lookup_realm(owning_team)
    try:
        return _predefined[(site, realm)]
    except KeyError:
        # This is ugly.  However, since NetDB contains all sorts of random
        # data for the "site" field, it's hard to do much better.  Throwing
        # an exception is not an option considering the low data quality.
        return _predefined[DEFAULT_BOUNCE_GROUP]


#
# AOL bounce window mapping. This should be moved to a configuration file.
#
# Bounce window documentation to be updated (eventually).
#
_b = BounceWindow
G = BounceStatus('green')
Y = BounceStatus('yellow')
R = BounceStatus('red')
_predefined = {         #   0     3     6     9     12    15    18    21
    ('TKP', 'BBEN'):    _b([Y,Y,Y,Y,Y,R,R,R,R,R,R,R,R,R,R,G,G,G,G,Y,Y,Y,Y,Y]),
    ('NTC', 'BBEN'):    _b([R,R,R,R,R,G,G,G,G,G,G,Y,Y,Y,Y,Y,R,R,R,R,R,R,R,R]),
    ('COL', 'BBEN'):    _b([R,Y,Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R]),
    ('COL', 'BBEN'):    _b([R,Y,Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R]),
    ('MTC', 'BBEN'):    _b([Y,Y,Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,R,R]),
    ('RTC', 'BBEN'):    _b([Y,Y,Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,R,R]),
    ('DTC', 'BBEN'):    _b([Y,Y,Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,R,R]),
    ('GTC', 'BBEN'):    _b([Y,Y,Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,R,R]),
    ('SPO', 'BBEN'):    _b([R,R,Y,G,G,G,Y,Y,Y,Y,R,R,R,R,R,R,R,R,R,R,R,R,R,R]),
    ('LOH', 'BBEN'):    _b([G,G,G,Y,Y,Y,Y,Y,R,R,R,R,R,R,R,R,R,R,R,R,R,R,R,G]),
    ('LEI', 'BBEN'):    _b([G,G,G,Y,Y,Y,Y,Y,R,R,R,R,R,R,R,R,R,R,R,R,R,R,R,G]),
    ('PRS', 'BBEN'):    _b([Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,Y,Y,Y,Y,G,G,G]),
    ('FRR', 'BBEN'):    _b([Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,Y,Y,Y,Y,G,G,G]),
    ('SYD', 'BBEN'):    _b([R,R,R,R,R,R,R,R,R,R,R,R,R,R,G,G,G,G,Y,Y,Y,Y,Y,R]),
    ('LUX', 'BBEN'):    _b([G,G,G,Y,Y,Y,Y,Y,R,R,R,R,R,R,R,R,R,R,R,R,R,R,R,G]),
    ('HOU', 'BBEN'):    _b([G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,Y,Y,Y,Y,G]),
    ('TKN', 'ATDN'):    _b([Y,Y,Y,Y,R,R,R,R,R,R,Y,Y,Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y]),
    ('JPIX', 'ATDN'):   _b([Y,Y,Y,Y,R,R,R,R,R,R,Y,Y,Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y]),
    ('HON', 'ATDN'):    _b([R,R,R,R,R,R,Y,Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y]),
    ('SJE', 'ATDN'):    _b([R,R,R,Y,Y,Y,G,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R]),
    ('SJG', 'ATDN'):    _b([R,R,R,Y,Y,Y,G,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R]),
    ('SEA', 'ATDN'):    _b([R,R,R,Y,Y,Y,G,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R]),
    ('NTC', 'ATDN'):    _b([R,R,R,Y,Y,Y,G,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R]),
    ('LA', 'ATDN'):     _b([R,R,R,Y,Y,Y,G,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R]),
    ('SUN', 'ATDN'):    _b([R,R,R,Y,Y,Y,G,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R]),
    ('PHO', 'ATDN'):    _b([R,R,Y,Y,Y,Y,G,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R]),
    ('DEN', 'ATDN'):    _b([R,R,Y,Y,Y,Y,G,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R]),
    ('COL', 'ATDN'):    _b([R,Y,Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R]),
    ('CIN', 'ATDN'):    _b([R,Y,Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R]),
    ('DAL', 'ATDN'):    _b([R,Y,Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R]),
    ('DKS', 'ATDN'):    _b([R,Y,Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R]),
    ('HOU', 'ATDN'):    _b([R,Y,Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R]),
    ('KCY', 'ATDN'):    _b([R,Y,Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R]),
    ('CHI', 'ATDN'):    _b([R,Y,Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R]),
    ('SPO', 'ATDN'):    _b([Y,Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,Y,Y]),
    ('ALB', 'ATDN'):    _b([Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R]),
    ('TBY', 'ATDN'):    _b([Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R]),
    ('ATL', 'ATDN'):    _b([Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,R,R,R,R,R,R]),
    ('MTC', 'ATDN'):    _b([Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,R,R,R,R,R,R]),
    ('RTC', 'ATDN'):    _b([Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,R,R,R,R,R,R]),
    ('DTC', 'ATDN'):    _b([Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,R,R,R,R,R,R]),
    ('ASH', 'ATDN'):    _b([Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,R,R,R,R,R,R]),
    ('VIE', 'ATDN'):    _b([Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,R,R,R,R,R,R]),
    ('CHA', 'ATDN'):    _b([Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,R,R,R,R,R,R]),
    ('ATM', 'ATDN'):    _b([Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,R,R,R,R,R,R]),
    ('NYE', 'ATDN'):    _b([Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,Y,Y,Y]),
    ('NYC', 'ATDN'):    _b([Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,Y,Y,Y]),
    ('NEW', 'ATDN'):    _b([Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,Y,Y,Y]),
    ('DCL', 'ATDN'):    _b([Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,Y,Y,Y]),
    ('LOH', 'ATDN'):    _b([G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,Y,Y,Y,G,G]),
    ('LON', 'ATDN'):    _b([G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,Y,Y,Y,G,G]),
    ('PAR', 'ATDN'):    _b([G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,Y,Y,Y,G,G]),
    ('PRS', 'ATDN'):    _b([G,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,Y,Y,Y,G,G]),
    ('FFR', 'ATDN'):    _b([Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,Y,Y,G,G,G]),
    ('FRA', 'ATDN'):    _b([Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,Y,Y,G,G,G]),
    ('CEN', 'BBEN'):    _b([Y,Y,R,R,R,R,R,R,R,R,R,R,R,R,R,R,R,R,R,R,G,G,G,Y]),
}

# Additions that are not in the list, sigh.
_predefined[('BRA', 'BBEN')] = _predefined[('LOH', 'BBEN')]
_predefined[('DUS', 'BBEN')] = _predefined[('FRR', 'BBEN')]
_predefined[('HAR', 'BBEN')] = _predefined[('LOH', 'BBEN')]
_predefined[('LBA', 'BBEN')] = _predefined[('LOH', 'BBEN')]
_predefined[('LOG', 'BBEN')] = _predefined[('LOH', 'BBEN')]
_predefined[('LOS', 'BBEN')] = _predefined[('LOH', 'BBEN')]
_predefined[('MAN', 'BBEN')] = _predefined[('LOH', 'BBEN')]
_predefined[('NQT', 'BBEN')] = _predefined[('LOH', 'BBEN')]
_predefined[('REA', 'BBEN')] = _predefined[('LOH', 'BBEN')]
_predefined[('SLO', 'BBEN')] = _predefined[('LOH', 'BBEN')]
_predefined[('STO', 'BBEN')] = _predefined[('LOH', 'BBEN')]
_predefined[('SZD', 'BBEN')] = _predefined[('LOH', 'BBEN')]
# and for ATDN:
_predefined[('FRR', 'ATDN')] = _predefined[('FRA', 'ATDN')]
_predefined[('DUS', 'ATDN')] = _predefined[('FRA', 'ATDN')]
_predefined[('PRX', 'ATDN')] = _predefined[('PRS', 'ATDN')]
