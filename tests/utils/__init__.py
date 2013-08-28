"""
Utils used for testing and especially mocking objects for testing.
"""

import mock_redis
import os
import sys

redis = mock_redis

def mock_redis_client(host=None, port=None, db=None):
    """Create a mock redis client"""
    return redis.Redis(host=host, port=port, db=db)

if __name__ == '__main__':
    os.environ['NETDEVICES_SOURCE'] = 'data/netdevices.xml'

    from trigger.netdevices import NetDevices
    from trigger.acl.db import AclsDB

    r = mock_redis_client(host=None, port=None, db=None)
    a = AclsDB()
    nd = NetDevices()

    dev = nd.find('test1-abc')

    print r.keys('*')
    print a.add_acl(dev, 'bacon')
    print r.keys('*')

    _k = 'acls:explicit:'
    key = _k + dev.nodeName

    print r.smembers(key)
