"""
Built-in dispatchers.

Try me with:

#!/usr/bin/env python

import sys

from twisted.python import log
log.startLogging(open('/tmp/dispatcher_test.log', 'a+'), setStdout=False)

from trigger.netdevices.dispatchers import core
from trigger.netdevices import NetDevices

nd = NetDevices()
device = nd.find('arista-sw1')

dispatcher = core.TriggerEndpointDispatcher(device)
dispatcher.open()

r = dispatcher.run_commands(['show clock', 'show version'])
"""

import re

from twisted.internet import defer

from trigger.conf import settings
from trigger.netdevices.dispatchers.base import BaseDispatcher
from trigger.netdevices.drivers.base import registry as driver_registry


class TriggerEndpointDispatcher(BaseDispatcher):

    def driver_connected(self):
        conn = self.driver._endpoint.transport.conn
        return bool(conn.channels)

    def get_driver(self):
        driver_class = driver_registry.drivers[self.device.vendor.name]
        driver = driver_class(
            hostname=self.device.nodeName,
            port=self.device.nodePort or settings.SSH_PORT,
            username=self.creds.username,
            password=self.creds.password,
        )

        return driver
