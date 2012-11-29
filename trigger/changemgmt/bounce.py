
# bounce.py - Attempting to further abstract bounce windows

from . import BounceStatus, BounceWindow

G = BounceStatus('green')
Y = BounceStatus('yellow')
R = BounceStatus('red')
BOUNCE_STATUS = {
    'green': G,
    'yellow': Y,
    'red': R
}

##        0     3     6     9     12    15    18    21
hours = [Y,Y,Y,Y,Y,G,G,G,Y,Y,Y,Y,Y,Y,Y,Y,R,R,R,R,R,R,R,R]
#        0     3     6     9     12    15    18    21
#hours = [G,G,G,Y,Y,Y,Y,Y,R,R,R,R,R,R,R,R,R,R,R,R,R,R,R,G]


class MyBounceWindow(BounceWindow):
    def __init__(self, status_by_hour=None, green=None, yellow=None, red=None,
                 default='red'):
        self._green = green
        self._yellow = yellow
        self._red = red
        self.default = default

        hours = {
            'green': self.parse_hours(green),
            'red':  self.parse_hours(red),
            'yellow':  self.parse_hours(yellow)
        }
        self.hours = hours
        self.hour_map = self.map_bounces(self.hours, default=default)

        # Allow for providing status_by_hour, but don't rely on it
        if status_by_hour is None:
            status_by_hour = self.hour_map.values()
        super(MyBounceWindow, self).__init__(status_by_hour=status_by_hour)

    def __repr__(self):
        #return "%s(green=%r, yellow=%r, red=%r, default=%r)" % (self.__class__.__name__, self._green, self._yellow, self._red, self.default)
        return "%s(green=%r, yellow=%r, red=%r)" % (self.__class__.__name__,
                                                    self._green, self._yellow,
                                                    self._red)

    def get_bounces(self, hours, color='red'):
        """Return a list of hours mapped to bounce objects"""
        return zip(hours, [BOUNCE_STATUS[color]] * len(hours))

    def map_bounces(self, hdict, default='red'):
        """
        Map a dictionary of colors and hours into a dictionary keyed by hour and
        the appropriate BounceStatus object.
        """
        status = []
        for color, hours in hdict.iteritems():
            status.extend(self.get_bounces(hours, color))

        # Fill in missing keys with the default color
        missing = [i for i in range(24) if i not in dict(status)]
        if missing:
            status.extend(self.get_bounces(missing, default))

        return dict(status)

    def parse_hours(self, hs):
        """
        Parse hour strings into lists of hours. Or if a list of hours is passed
        in, just return it as is.

        >>> parse_hours('0-3, 23')
        [0, 1, 2, 3, 23]
        parse_hours(range(3)) 
        [0, 1, 2]
        """
        myhours = []
        if hs is None:
            return myhours

        if isinstance(hs, list):
            return hs

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

_B = MyBounceWindow
# Red is the default for any hours not specified
_predefined = {
    ('ALB', 'ATDN'): _B(green='3-5', yellow='0-2, 6-18', red='19-23'),
    ('ASH', 'ATDN'): _B(green='3-5', yellow='0-2, 6-11', red='12-23'),
    ('ATC', 'BBEN'): _B(green='5-7', yellow='0-4, 8-15', red='16-23'),
    ('ATL', 'ATDN'): _B(green='3-5', yellow='0-2, 6-11', red='12-23'),
    ('ATM', 'ATDN'): _B(green='3-5', yellow='0-2, 6-11', red='12-23'),
    ('BRA', 'BBEN'): _B(green='0-2, 23', yellow='3-7', red='8-22'),
    ('CEN', 'BBEN'): _B(green='20-22', yellow='0-1, 23', red='2-19'),
    ('CHA', 'ATDN'): _B(green='3-5', yellow='0-2, 6-11', red='12-23'),
    ('CHI', 'ATDN'): _B(green='5-7', yellow='1-4, 8-18', red='0, 19-23'),
    ('CIN', 'ATDN'): _B(green='5-7', yellow='1-4, 8-18', red='0, 19-23'),
    ('COL', 'ATDN'): _B(green='5-7', yellow='1-4, 8-18', red='0, 19-23'),
    ('COL', 'BBEN'): _B(green='5-7', yellow='1-4, 8-18', red='0, 19-23'),
    ('DAL', 'ATDN'): _B(green='5-7', yellow='1-4, 8-18', red='0, 19-23'),
    ('DCL', 'ATDN'): _B(green='2-4', yellow='0-1, 5-14, 21-23', red='15-20'),
    ('DEN', 'ATDN'): _B(green='6-9', yellow='2-5, 10-19', red='0-1, 20-23'),
    ('DKS', 'ATDN'): _B(green='5-7', yellow='1-4, 8-18', red='0, 19-23'),
    ('DTC', 'ATDN'): _B(green='3-5', yellow='0-2, 6-11', red='12-23'),
    ('DTC', 'BBEN'): _B(green='5-7', yellow='0-4, 8-15', red='16-23'),
    ('DUS', 'ATDN'): _B(green='21-23', yellow='0-12, 19-20', red='13-18'),
    ('DUS', 'BBEN'): _B(green='21-23', yellow='0-12, 17-20', red='13-16'),
    ('FFR', 'ATDN'): _B(green='21-23', yellow='0-12, 19-20', red='13-18'),
    ('FRR', 'ATDN'): _B(green='21-23', yellow='0-12, 19-20', red='13-18'),
    ('FRR', 'BBEN'): _B(green='21-23', yellow='0-12, 17-20', red='13-16'),
    ('GTC', 'BBEN'): _B(green='5-7', yellow='0-4, 8-15', red='16-23'),
    ('HON', 'ATDN'): _B(green='10-12', yellow='6-9, 13-23', red='0-5'),
    ('HOU', 'ATDN'): _B(green='5-7', yellow='1-4, 8-18', red='0, 19-23'),
    ('HOU', 'BBEN'): _B(green='0, 23', yellow='1-12, 19-22', red='13-18'),
    ('KCY', 'ATDN'): _B(green='5-7', yellow='1-4, 8-18', red='0, 19-23'),
    ('LAS', 'ATDN'): _B(green='6-9', yellow='3-5, 10-20', red='0-2, 21-23'),
    ('LBA', 'BBEN'): _B(green='0-2, 23', yellow='3-7', red='8-22'),
    ('LEI', 'BBEN'): _B(green='0-2, 23', yellow='3-7', red='8-22'),
    ('LOG', 'BBEN'): _B(green='0-2, 23', yellow='3-7', red='8-22'),
    ('LOH', 'ATDN'): _B(green='0, 22-23', yellow='1-12, 19-21', red='13-18'),
    ('LOH', 'BBEN'): _B(green='0-2, 23', yellow='3-7', red='8-22'),
    ('LON', 'ATDN'): _B(green='0, 22-23', yellow='1-12, 19-21', red='13-18'),
    ('LOS', 'BBEN'): _B(green='0-2, 23', yellow='3-7', red='8-22'),
    ('LUX', 'BBEN'): _B(green='0-2, 23', yellow='3-7', red='8-22'),
    ('MTC', 'ATDN'): _B(green='3-5', yellow='0-2, 6-11', red='12-23'),
    ('MTC', 'BBEN'): _B(green='5-7', yellow='0-4, 8-15', red='16-23'),
    ('NEW', 'ATDN'): _B(green='2-4', yellow='0-1, 5-14, 21-23', red='15-20'),
    ('NTC', 'ATDN'): _B(green='6-9', yellow='3-5, 10-20', red='0-2, 21-23'),
    ('NTC', 'BBEN'): _B(green='5-10', yellow='11-15', red='0-4, 16-23'),
    ('NYC', 'ATDN'): _B(green='2-4', yellow='0-1, 5-14, 21-23', red='15-20'),
    ('NYE', 'ATDN'): _B(green='2-4', yellow='0-1, 5-14, 21-23', red='15-20'),
    ('NYK', 'ATDN'): _B(green='2-4', yellow='0-1, 5-14, 21-23', red='15-20'),
    ('NYW', 'ATDN'): _B(green='2-4', yellow='0-1, 5-14, 21-23', red='15-20'),
    ('PAR', 'ATDN'): _B(green='0, 22-23', yellow='1-12, 19-21', red='13-18'),
    ('PHO', 'ATDN'): _B(green='6-9', yellow='2-5, 10-19', red='0-1, 20-23'),
    ('PRS', 'ATDN'): _B(green='0, 22-23', yellow='1-12, 19-21', red='13-18'),
    ('PRS', 'BBEN'): _B(green='21-23', yellow='0-12, 17-20', red='13-16'),
    ('PRX', 'ATDN'): _B(green='0, 22-23', yellow='1-12, 19-21', red='13-18'),
    ('REA', 'BBEN'): _B(green='0-2, 23', yellow='3-7', red='8-22'),
    ('RTC', 'ATDN'): _B(green='3-5', yellow='0-2, 6-11', red='12-23'),
    ('RTC', 'BBEN'): _B(green='5-7', yellow='0-4, 8-15', red='16-23'),
    ('SEA', 'ATDN'): _B(green='6-9', yellow='3-5, 10-20', red='0-2, 21-23'),
    ('SJG', 'ATDN'): _B(green='6-9', yellow='3-5, 10-20', red='0-2, 21-23'),
    ('SLO', 'BBEN'): _B(green='0-2, 23', yellow='3-7', red='8-22'),
    ('SPO', 'ATDN'): _B(green='4-6', yellow='0-3, 7-15, 22-23', red='16-21'),
    ('SPO', 'BBEN'): _B(green='3-5', yellow='2, 6-9', red='0-1, 10-23'),
    ('STO', 'BBEN'): _B(green='0-2, 23', yellow='3-7', red='8-22'),
    ('SUN', 'ATDN'): _B(green='6-9', yellow='3-5, 10-20', red='0-2, 21-23'),
    ('SYD', 'BBEN'): _B(green='14-17', yellow='18-22', red='0-13, 23'),
    ('SZD', 'BBEN'): _B(green='0-2, 23', yellow='3-7', red='8-22'),
    ('TBY', 'ATDN'): _B(green='3-5', yellow='0-2, 6-18', red='19-23'),
    ('TKN', 'ATDN'): _B(green='15-17', yellow='0-3, 10-14, 18-23', red='4-9'),
    ('TKP', 'BBEN'): _B(green='15-18', yellow='0-4, 19-23', red='5-14'),
    ('VIE', 'ATDN'): _B(green='3-5', yellow='0-2, 6-11', red='12-23')
}
