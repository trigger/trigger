"""
Utils used for testing and especially mocking objects for testing.
"""

import mock_redis
import os
import sys

__all__ = ['mock_redis']

# misc
from . import misc
from misc import *
__all__.extend(misc.__all__)

if __name__ == '__main__':
    os.environ['NETDEVICES_SOURCE'] = 'data/netdevices.xml'

    mock_redis.install()
    import redis
    from trigger.netdevices import NetDevices
    from trigger.acl.db import AclsDB

    r = redis.Redis()
    a = AclsDB()
    nd = NetDevices()

    dev = nd.find('test1-abc')

    print r.keys('*')
    print a.add_acl(dev, 'bacon')
    print r.keys('*')

    _k = 'acls:explicit:'
    key = _k + dev.nodeName

    print r.smembers(key)
