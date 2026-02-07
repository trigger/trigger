"""
Utils used for testing and especially mocking objects for testing.
"""

import os
import sys  # noqa: F401

from . import mock_redis

__all__ = ["mock_redis"]

# misc
from . import misc
from .misc import *  # noqa: F403

__all__.extend(misc.__all__)

if __name__ == "__main__":
    os.environ["NETDEVICES_SOURCE"] = "data/netdevices.xml"

    mock_redis.install()
    import redis

    from trigger.acl.db import AclsDB
    from trigger.netdevices import NetDevices

    r = redis.Redis()
    a = AclsDB()
    nd = NetDevices()

    dev = nd.find("test1-abc")

    print(r.keys("*"))
    print(a.add_acl(dev, "bacon"))
    print(r.keys("*"))

    _k = "acls:explicit:"
    key = _k + dev.nodeName

    print(r.smembers(key))
