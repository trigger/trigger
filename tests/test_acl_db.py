#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test the functionality of `~trigger.acl.db` (aka ACLs.db)
"""

# Make sure we load the mock redis library
from utils import mock_redis
mock_redis.install()

# And now we can load the Trigger libs that call Redis
from trigger.netdevices import NetDevices
from trigger.acl.db import AclsDB
from trigger import exceptions
import unittest

# Globals
adb = AclsDB()
DEVICE_NAME = 'test1-abc.net.aol.com'
ACL_NAME = 'foo'

class TestAclsDB(unittest.TestCase):
    def setUp(self):
        self.nd = NetDevices()
        self.acl = ACL_NAME
        self.device = self.nd.find(DEVICE_NAME)
        self.implicit_acls = set(['115j', 'router-protect.core'])

    def test_01_add_acl_success(self):
        """Test associate ACL to device success"""
        exp = 'added acl %s to %s' % (self.acl, self.device)
        self.assertEqual(exp, adb.add_acl(self.device, self.acl))

    def test_02_add_acl_failure(self):
        """Test associate ACL to device failure"""
        exp = exceptions.ACLSetError
        self.assertRaises(exp, adb.add_acl, self.device, self.acl)

    def test_03_remove_acl_success(self):
        """Test remove ACL from device success"""
        exp = 'removed acl %s from %s' % (self.acl, self.device)
        self.assertEqual(exp, adb.remove_acl(self.device, self.acl))

    def test_04_remove_acl_failure(self):
        """Test remove ACL from device failure"""
        exp = exceptions.ACLSetError
        self.assertRaises(exp, adb.remove_acl, self.device, self.acl)

    def test_05_get_acl_dict(self):
        """Test get dict of associations"""
        exp = {'all': self.implicit_acls, 'explicit': set(),
               'implicit': self.implicit_acls}
        self.assertEqual(exp, adb.get_acl_dict(self.device))

    def test_06_get_acl_set_success(self):
        """Test get set of associations success"""
        exp = self.implicit_acls
        self.assertEqual(exp, adb.get_acl_set(self.device))

    def test_07_get_acl_set_failure(self):
        """Test get set of associations failure"""
        exp = exceptions.InvalidACLSet
        acl_set = 'bogus'
        self.assertRaises(exp, adb.get_acl_set, self.device, acl_set)

    def tearDown(self):
        NetDevices._Singleton = None

if __name__ == '__main__':
    unittest.main()
