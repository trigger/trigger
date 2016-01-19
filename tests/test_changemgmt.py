#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for bounce windows and the stuff that goes with them.
"""

__author__ = 'Jathan McCollum, Michael Shields'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jmccollum@salesforce.com'
__copyright__ = 'Copyright 2013 Salesforce.com'
__version__ = '2.0'


# Make sure we load the mock redis library
from utils import mock_redis
mock_redis.install()

from datetime import datetime
from pytz import timezone, UTC
from trigger.changemgmt import BounceStatus, BounceWindow
from trigger.netdevices import NetDevices
import unittest


# Globals
eastern = timezone('US/Eastern')
pacific = timezone('US/Pacific')


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
        self.eastern = BounceWindow(green='5-7', yellow='8-11')
        self.pacific = BounceWindow(green='2-4', yellow='5-7')

    def testStatus(self):
        """Test lookup of bounce window status."""
        # 00:00 UTC, 19:00 EST
        when = datetime(2006, 1, 3, tzinfo=UTC)
        self.assertEquals(self.eastern.status(when), 'red')
        # 03:00 PST, 14:00 UTC
        then = pacific.localize(datetime(2013, 6, 4))
        self.assertEquals(self.pacific.status(then), 'green')

    def testNextOk(self):
        """Test bounce window next_ok() method."""
        when = datetime(2013, 1, 3, 22, 15, tzinfo=UTC)
        next_ok = self.pacific.next_ok('yellow', when)
        # Did we get the right answer?  (2 am PST the next morning)
        self.assertEquals(next_ok.tzinfo, UTC)
        self.assertEquals(next_ok.astimezone(eastern).hour, 2)
        self.assertEquals(next_ok, datetime(2013, 1, 4, 7, 0, tzinfo=UTC))
        self.assertEquals(self.pacific.status(next_ok), 'green')
        # next_ok() should return current time if already ok.
        self.assertEquals(self.pacific.next_ok('yellow', next_ok), next_ok)
        then = datetime(2013, 1, 3, 22, 15, tzinfo=UTC)
        self.assertEquals(self.pacific.next_ok('red', then), then)

class CheckWeekend(unittest.TestCase):
    def testWeekend(self):
        """Test weekend moratorium."""
        when = datetime(2006, 1, 6, 20, tzinfo=UTC)
        next_ok = BounceWindow(green='5-7', yellow='8-11').next_ok('green', when)
        self.assertEquals(next_ok, datetime(2006, 1, 9, 10, tzinfo=UTC))

class CheckNetDevices(unittest.TestCase):
    def setUp(self):
        self.router = NetDevices()['test1-abc.net.aol.com']
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
