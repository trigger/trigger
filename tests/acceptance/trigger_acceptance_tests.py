#!/usr/bin/env python
"""
tests/trigger_acceptance_test.py - Acceptance test suite that verifies trigger functionality
in very brief
"""

from trigger.netdevices import NetDevices

netdevices = NetDevices(with_acls=False)
nd = NetDevices(with_acls=False)
print(list(nd.values()))

__author__ = "Murat Ezbiderli"
__maintainer__ = "Salesforce"
__copyright__ = "Copyright 2012-2013 Salesforce Inc."
__version__ = "2.1"

import unittest

from trigger.netdevices import NetDevices


class NetDevicesTest(unittest.TestCase):
    def setUp(self):
        self.nd = NetDevices(with_acls=False)
        print(list(self.nd.values()))
        self.nodename = next(iter(self.nd.keys()))
        self.nodeobj = next(iter(self.nd.values()))

    def testBasics(self):
        """Basic test of NetDevices functionality."""
        self.assertEqual(len(self.nd), 3)
        self.assertEqual(self.nodeobj.nodeName, self.nodename)
        self.assertEqual(self.nodeobj.manufacturer, "JUNIPER")

    def testFind(self):
        """Test the find() method."""
        self.assertEqual(self.nd.find(self.nodename), self.nodeobj)
        nodebasename = self.nodename[: self.nodename.index(".")]
        self.assertEqual(self.nd.find(nodebasename), self.nodeobj)
        self.assertRaises(KeyError, lambda: self.nd.find(self.nodename[0:3]))


if __name__ == "__main__":
    unittest.main()
