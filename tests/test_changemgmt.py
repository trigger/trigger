#!/usr/bin/env python
# -*- coding: utf-8 -*-

# tests/changemgmt.py

__author__ = 'Michael Shields'
__maintainer__ = 'Jathan McCollum'
__copyright__ = 'Copyright 2005-2011 AOL Inc.'
__version__ = '1.1'

import unittest
from datetime import datetime
from pytz import timezone, UTC
from trigger.changemgmt import site_bounce, BounceStatus
from trigger.netdevices import NetDevices


ET = timezone('US/Eastern')


class CheckBounceStatus(unittest.TestCase):
    def setUp(self):
        self.red = BounceStatus('red')
        self.green = BounceStatus('green')
        self.yellow = BounceStatus('yellow')

    def testComparison(self):
        """Test comparison of BounceStatus against BounceStatus."""
        self.assert_(self.red > self.yellow > self.green)
        self.assert_(self.red == self.red == BounceStatus('red'))
        self.assertNotEquals(self.red, self.yellow)

    def testString(self):
        """Test BounceStatus stringfication and string comparison."""
        self.assertEquals(str(self.red), 'red')
        self.assertEquals(self.red, 'red')
        self.assert_('red' > self.yellow > 'green')

class CheckBounceWindow(unittest.TestCase):
    def setUp(self):
        self.dtc = site_bounce('DTC')
        self.dtc_atdn = site_bounce('DTC', oncallid='80')
        self.ntc = site_bounce('NTC')

    def testStatus(self):
        """Test lookup of bounce window status."""
        # 00:00 UTC, 19:00 EST
        when = datetime(2006, 1, 3, tzinfo=UTC)
        self.assertEquals(self.dtc.status(when), 'red')
        # 00:00 EST, 05:00 UTC
        when = datetime(2006, 1, 3, tzinfo=ET)
        self.assertEquals(self.dtc_atdn.status(when), 'yellow')

    def testNextOk(self):
        """Test bounce window next_ok() method."""
        when = datetime(2006, 1, 3, 22, 15, tzinfo=UTC)
        next_ok = self.ntc.next_ok('yellow', when)
        # Did we get the right answer?  (2 am PST the next morning)
        self.assertEquals(next_ok.tzinfo, UTC)
        self.assertEquals(next_ok.astimezone(ET).hour, 5)
        self.assertEquals(next_ok, datetime(2006, 1, 4, 10, 0, tzinfo=UTC))
        self.assertEquals(self.ntc.status(next_ok), 'green')
        # next_ok() should return current time if already ok.
        self.assertEquals(self.ntc.next_ok('yellow', next_ok), next_ok)
        when = datetime(2006, 1, 3, 22, 15, tzinfo=UTC)
        self.assertEquals(self.ntc.next_ok('red', when), when)

class CheckWeekend(unittest.TestCase):
    def testWeekend(self):
        """Test weekend moratorium."""
        when = datetime(2006, 1, 6, 20, tzinfo=UTC)
        next_ok = site_bounce('DTC').next_ok('green', when)
        self.assertEquals(next_ok, datetime(2006, 1, 9, 10, tzinfo=UTC))

class CheckNetDevices(unittest.TestCase):
    def setUp(self):
        self.router = NetDevices()['iwg1-r3.router.aol.com']
        self.when = datetime(2006, 7, 24, 20, tzinfo=UTC)

    def testNetDevicesBounce(self):
        """Test integration of bounce windows with NetDevices."""
        self.assertEquals(self.router.bounce.status(self.when), 'red')

    def testAllowability(self):
        """Test allowability checks."""
        self.failIf(self.router.allowable('load-acl', self.when))
        morning = datetime(2006, 7, 25, 9, tzinfo=UTC)        # 5 am EDT
        self.assert_(self.router.allowable('load-acl', morning))
        self.assertEquals(self.router.next_ok('load-acl', self.when), morning)
        self.assertEquals(self.router.next_ok('load-acl', morning), morning)


if __name__ == "__main__":
    unittest.main()
