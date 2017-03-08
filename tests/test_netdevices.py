#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test the functionality of NetDevice, NetDevices, and Vendor objects.

This uses the mockups of netdevices.xml, acls.db, and autoacls.py in
tests/data.
"""

__author__ = 'Jathan McCollum, Michael Shields'
__maintainer__ = 'Jathan McCollum'
__copyright__ = 'Copyright 2005-2011 AOL Inc.; 2013 Salesforce.com'
__version__ = '2.0'

import os
import unittest

# Make sure we load the mock redis library
from utils import captured_output
from utils import mock_redis
mock_redis.install()

# Now we can import from Trigger
from trigger.netdevices import NetDevices, NetDevice, Vendor
from trigger import changemgmt


# Constants
DEVICE_NAME = 'test1-abc.net.aol.com'
DEVICE2_NAME = 'test2-abc.net.aol.com'
NETDEVICE_DUMP_EXPECTED = \
'\n\tHostname:          test1-abc.net.aol.com\n\tOwning Org.:       12345678 - Network Engineering\n\tOwning Team:       Data Center\n\tOnCall Team:       Data Center\n\n\tVendor:            Juniper (JUNIPER)\n\tMake:              M40 INTERNET BACKBONE ROUTER\n\tModel:             M40-B-AC\n\tType:              ROUTER\n\tLocation:          LAB CR10 16ZZ\n\n\tProject:           Test Lab\n\tSerial:            987654321\n\tAsset Tag:         0000012345\n\tBudget Code:       1234578 (Data Center)\n\n\tAdmin Status:      PRODUCTION\n\tLifecycle Status:  INSTALLED\n\tOperation Status:  MONITORED\n\tLast Updated:      2010-07-19 19:56:32.0\n\n'


def _reset_netdevices():
    """Reset the Singleton state of NetDevices class."""
    NetDevices._Singleton = None


class TestNetDevicesWithAcls(unittest.TestCase):
    """
    Test NetDevices with ``settings.WITH_ACLs set`` to ``True``.
    """
    def setUp(self):
        self.nd = NetDevices()
        self.device = self.nd[DEVICE_NAME]
        self.device2 = self.nd[DEVICE2_NAME]
        self.nodename = self.device.nodeName
        self.device.explicit_acls = set(['test1-abc-only'])

    def test_basics(self):
        """Basic test of NetDevices functionality."""
        self.assertEqual(len(self.nd), 2)
        self.assertEqual(self.device.nodeName, self.nodename)
        self.assertEqual(self.device.manufacturer, 'JUNIPER')

    def test_aclsdb(self):
        """Test acls.db handling."""
        self.assertTrue('test1-abc-only' in self.device.explicit_acls)

    def test_autoacls(self):
        """Test autoacls.py handling."""
        self.assertTrue('router-protect.core' in self.device.implicit_acls)

    def test_find(self):
        """Test the find() method."""
        self.assertEqual(self.nd.find(self.nodename), self.device)
        nodebasename = self.nodename[:self.nodename.index('.')]
        self.assertEqual(self.nd.find(nodebasename), self.device)
        self.assertRaises(KeyError, lambda: self.nd.find(self.nodename[0:3]))

    def test_all(self):
        """Test the all() method."""
        expected = [self.device, self.device2]
        self.assertEqual(sorted(expected), sorted(self.nd.all()))

    def test_search(self):
        """Test the search() method."""
        expected = [self.device]
        self.assertEqual([self.device], self.nd.search(self.nodename))
        self.assertEqual(self.nd.all(), self.nd.search('17', field='onCallID'))

    def test_match(self):
        """Test the match() method."""
        self.assertEqual([self.device], self.nd.match(nodename=self.nodename))
        self.assertEqual(self.nd.all(), self.nd.match(vendor='juniper'))
        self.assertEqual([], self.nd.match(vendor='cisco'))

    def test_multiple_filter_match(self):
        """Test that passing multiple kwargs filters properly."""
        # There should be only one Juniper router.
        self.assertEqual(
            self.nd.match(nodename='test1-abc'),
            self.nd.match(vendor='juniper', devicetype='router')
        )

        # And only one Juniper switch.
        self.assertEqual(
            self.nd.match(nodename='test2-abc'),
            self.nd.match(vendor='juniper', devicetype='switch')
        )

    def test_match_with_null_value(self):
        """Test the match() method when attr value is ``None``."""
        self.device.site = None  # Zero it out!
        expected = [self.device]

        # None raw
        self.assertEqual(expected, self.nd.match(site=None))

        # "None" string
        self.assertEqual(expected, self.nd.match(site='None'))

        # Case-insensitive attr *and* value
        self.assertEqual(expected, self.nd.match(SITE='NONE'))

    def test_reload(self):
        """Test the .reload() method."""
        nd = self.nd
        nd.reload()
        self.assertEqual(nd, self.nd)

    def tearDown(self):
        _reset_netdevices()


class TestNetDevicesWithoutAcls(unittest.TestCase):
    """
    Test NetDevices with ``settings.WITH_ACLs`` set to ``False``.
    """
    def setUp(self):
        self.nd = NetDevices(with_acls=False)
        self.nodename = self.nd.keys()[0]
        self.device = self.nd.values()[0]

    def test_aclsdb(self):
        """Test acls.db handling."""
        self.assertFalse('test1-abc-only' in self.device.explicit_acls)

    def test_autoacls(self):
        """Test autoacls.py handling."""
        expected = set()
        self.assertEqual(expected, self.device.implicit_acls)

    def tearDown(self):
        _reset_netdevices()


class TestNetDeviceObject(unittest.TestCase):
    """
    Test NetDevice object methods.
    """
    def setUp(self):
        self.nd = NetDevices()
        self.device = self.nd[DEVICE_NAME]
        self.nodename = self.device.nodeName

    def test_stringify(self):
        """Test casting NetDevice to string"""
        expected = self.nodename
        self.assertEqual(expected, str(self.device))

    def test_bounce(self):
        """Test .bounce property"""
        expected = changemgmt.BounceWindow
        self.assertTrue(isinstance(self.device.bounce, expected))

    def test_shortName(self):
        """Test .shortName property"""
        expected = self.nodename.split('.', 1)[0]
        self.assertEqual(expected, self.device.shortName)

    def test_allowable(self):
        """Test allowable() method"""
        # This is already tested in test_changemgmt.py, so this is a stub.
        pass

    def test_next_ok(self):
        """Test next_ok() method"""
        # This is already tested in test_changemgmt.py, so this is a stub.
        pass

    def test_identity(self):
        """Exercise NetDevice identity tests."""
        # It's a router...
        self.assertTrue(self.device.is_router())
        # And therefore none of these other things...
        self.assertFalse(self.device.is_switch())
        self.assertFalse(self.device.is_firewall())
        self.assertFalse(self.device.is_netscaler())
        self.assertFalse(self.device.is_netscreen())
        self.assertFalse(self.device.is_ioslike())
        self.assertFalse(self.device.is_brocade_vdx())

    def test_hash_ssh(self):
        """Exercise NetDevice ssh test."""
        # TODO (jathan): Mock SSH connections so we can test actual connectivity
        # Device won't be reachable, so this should always fail
        self.assertFalse(self.device.has_ssh())
        # Since there's no SSH, no aync
        self.assertFalse(self.device.can_ssh_pty())

    def test_reachability(self):
        """Exercise NetDevice ssh test."""
        # TODO (jathan): Mock SSH connections so we can test actual connectivity
        self.assertFalse(self.device.is_reachable())

    def test_dump(self):
        """Test the dump() method."""
        with captured_output() as (out, err):
            self.device.dump()
        expected = NETDEVICE_DUMP_EXPECTED
        output = out.getvalue()
        self.assertEqual(expected, output)

    def test_os(self):
        self.nd = NetDevices()
        self.device = self.nd[DEVICE_NAME]
        self.device.vendor = "cisco"
        self.device.operatingSystem = "NXOS"
        self.nodename = self.device.nodeName
        self.assertEquals("cisco_nxos", self.device.os)

    def tearDown(self):
        _reset_netdevices()


class TestVendorObject(unittest.TestCase):
    """Test Vendor object"""
    def setUp(self):
        self.mfr = 'CISCO SYSTEMS'
        self.vendor = Vendor(self.mfr)

    def test_creation(self):
        """Test creation of a Vendor instance"""
        expected = 'cisco'
        self.assertEqual(expected, self.vendor)

    def test_string_operations(self):
        """Test string output and comparison behaviors"""
        # String comparisons
        expected = 'cisco'
        self.assertEqual(expected, self.vendor.normalized)
        self.assertEqual(expected, str(self.vendor))
        self.assertEqual(expected, Vendor(expected))
        # Title casing
        expected = 'Cisco'
        self.assertEqual(expected, self.vendor.title)
        self.assertEqual(expected.lower(), self.vendor.lower())
        # Mfr equates to object
        self.assertEqual(self.mfr, self.vendor)

    def test_membership(self):
        """Test membership w/ __eq__ and __contains__"""
        expected = 'cisco'
        self.assertTrue(expected in [self.vendor])
        self.assertTrue(self.vendor in [self.vendor])
        self.assertTrue(self.vendor in [expected])
        self.assertFalse(self.vendor in ['juniper', 'foundry'])

    def test_determine_vendor(self):
        """Test determine_vendor() method"""
        expected = 'cisco'
        self.assertEqual(expected, self.vendor.determine_vendor(self.mfr))


if __name__ == "__main__":
    unittest.main()
