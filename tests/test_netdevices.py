#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
tests/netdevices.py - This uses the mockups of netdevices.xml, acls.db, and
autoacls.py in tests/data.
"""

__author__ = 'Michael Shields'
__maintainer__ = 'Jathan McCollum'
__copyright__ = 'Copyright 2005-2011 AOL Inc.'
__version__ = '1.1'

import os
import unittest

from trigger.netdevices import NetDevices

class NetDevicesTest(unittest.TestCase):

    def setUp(self):
        self.nd = NetDevices()
        self.nodename = self.nd.keys()[0]
        self.nodeobj = self.nd.values()[0]

    def testBasics(self):
        """Basic test of NetDevices functionality."""
        self.assertEqual(len(self.nd), 1)
        self.assertEqual(self.nodeobj.nodeName, self.nodename)
        self.assertEqual(self.nodeobj.manufacturer, 'JUNIPER')

    def testAclsdb(self):
        """Test acls.db handling."""
        self.assert_('181j' in self.nodeobj.acls)

    def testAutoacls(self):
        """Test autoacls.py handling."""
        self.assert_('115j' in self.nodeobj.acls)

    def testFind(self):
        """Test the find() method."""
        self.assertEqual(self.nd.find(self.nodename), self.nodeobj)
        nodebasename = self.nodename[:self.nodename.index('.')]
        self.assertEqual(self.nd.find(nodebasename), self.nodeobj)
        self.assertRaises(KeyError, lambda: self.nd.find(self.nodename[0:3]))

if __name__ == "__main__":
    unittest.main()
