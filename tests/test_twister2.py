#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test the functionality of TriggerSSHShellClientEndpoint.

This uses the mockups of netdevices.xml in
tests/data.
"""

__author__ = 'Thomas Cuthbert, Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__copyright__ = 'Copyright 2005-2011 AOL Inc.; 2013 Salesforce.com.; 2016 Dropbox'
__version__ = '1.0'

import os
import unittest

# from utils import captured_output

# Now we can import from Trigger
# from trigger.netdevices import NetDevices, NetDevice, Vendor
from trigger.twister2 import TriggerSSHShellClientEndpointBase


class TestTriggerSSHShellClientEndpointBase(unittest.TestCase):
    """
    Test TriggerSSHShellClientEndpoint with defaults.
    """
    def setUp(self):
        self.endpoint = TriggerSSHShellClientEndpointBase

    def testInit(self):
       self.assertTrue(self.endpoint)


class Test_NewConnectionHelper(unittest.TestCase):
    pass
