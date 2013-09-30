#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test the functionality of `~trigger.acl.queue` (aka task queue)

Only tests SQLite for now.
"""

import datetime
import os
import tempfile
from trigger.conf import settings

# Override the DB file we're going to use.
_, db_file = tempfile.mkstemp('.db')
settings.DATABASE_NAME = db_file

# Make sure we load the mock redis library
from utils import mock_redis
mock_redis.install()

# Now we can import from Trigger
from trigger.acl import queue
from trigger.acl.models import create_tables
from trigger.acl.db import AclsDB
from trigger.netdevices import NetDevices
from trigger.utils import get_user
from trigger import exceptions
import unittest

# Globals
DEVICE_NAME = 'test1-abc.net.aol.com'
ACL_NAME = 'foo'
USERNAME = get_user()

# Setup
create_tables()
adb = AclsDB()
nd = NetDevices()
# These must happen after we populate the dummy AclsDB

def _setup_aclsdb(nd, device_name=DEVICE_NAME, acl=ACL_NAME):
    """Add an explicit ACL to the dummy AclsDB"""
    #print 'Setting up ACLsdb: %s => %s' % (acl, device_name)
    dev = nd.find(device_name)
    if acl not in dev.acls:
        adb.add_acl(dev, acl)
    NetDevices._Singleton = None
    nd = NetDevices()

class TestAclQueue(unittest.TestCase):
    def setUp(self):
        self.nd = NetDevices()
        _setup_aclsdb(self.nd)
        self.q = queue.Queue(verbose=False)
        self.acl = ACL_NAME
        self.acl_list = [self.acl]
        self.device = self.nd.find(DEVICE_NAME)
        self.device_name = DEVICE_NAME
        self.device_list = [self.device_name]
        self.user = USERNAME

    #
    # Integrated queue tests
    #

    def test_01_insert_integrated_success(self):
        """Test insert success into integrated queue"""
        self.assertTrue(self.q.insert(self.acl, self.device_list) is None)

    def test_02_insert_integrated_failure_device(self):
        """Test insert invalid device"""
        self.assertRaises(exceptions.TriggerError, self.q.insert, self.acl, ['bogus'])

    def test_03_insert_integrated_failure_acl(self):
        """Test insert devices w/ no ACL association"""
        self.assertRaises(exceptions.TriggerError, self.q.insert, 'bogus',
                          self.device_list)

    def test_04_list_integrated_success(self):
        """Test listing integrated queue"""
        self.q.insert(self.acl, self.device_list)
        expected = [(u'test1-abc.net.aol.com', u'foo')]
        self.assertEqual(sorted(expected), sorted(self.q.list()))

    def test_05_complete_integrated(self):
        """Test mark task complete"""
        self.q.complete(self.device_name, self.acl_list)
        expected = []
        self.assertEqual(sorted(expected), sorted(self.q.list()))

    def test_06_delete_integrated_with_devices(self):
        """Test delete ACL from queue providing devices"""
        self.q.insert(self.acl, self.device_list)
        self.assertTrue(self.q.delete(self.acl, self.device_list))

    def test_07_delete_integrated_no_devices(self):
        """Test delete ACL from queue without providing devices"""
        self.q.insert(self.acl, self.device_list)
        self.assertTrue(self.q.delete(self.acl))

    def test_08_remove_integrated_success(self):
        """Test remove (set as loaded) ACL from integrated queue"""
        self.q.insert(self.acl, self.device_list)
        self.q.remove(self.acl, self.device_list)
        expected = []
        self.assertEqual(sorted(expected), sorted(self.q.list()))

    def test_10_remove_integrated_failure(self):
        """Test remove (set as loaded) failure"""
        self.assertRaises(exceptions.ACLQueueError, self.q.remove, '', self.device_list)

    #
    # Manual queue tests
    #

    def test_11_insert_manual_success(self):
        """Test insert success into manual queue"""
        self.assertTrue(self.q.insert('manual task', None) is None)

    def test_12_list_manual_success(self):
        """Test list success of manual queue"""
        self.q.insert('manual task', None)
        expected = ('manual task', self.user)
        result = self.q.list('manual')
        actual = result[0][:2] # First tuple, items 0-1
        self.assertEqual(sorted(expected), sorted(actual))

    def test_13_delete_manual_success(self):
        """Test delete from manual queue"""
        self.q.delete('manual task')
        expected = []
        self.assertEqual(sorted(expected), sorted(self.q.list('manual')))

    #
    # Generic tests
    #

    def test_14_delete_failure(self):
        """Test delete of task not in queue"""
        self.assertFalse(self.q.delete('bogus'))

    def test_15_list_invalid(self):
        """Test list of invalid queue name"""
        self.assertFalse(self.q.list('bogus'))

    # Teardown

    def test_ZZ_cleanup_db(self):
        """Cleanup the temp database file"""
        self.assertTrue(os.remove(db_file) is None)

    def tearDown(self):
        NetDevices._Singleton = None

if __name__ == '__main__':
    unittest.main()
