"""
Napalm handler.

Try me with:

#!/usr/bin/env python

import sys

from twisted.python import log
log.startLogging(open('/tmp/napalm_handler_test.log', 'a+'), setStdout=False)

from trigger.netdevices import NetDevices
from trigger.netdevices.handlers import napalm

nd = NetDevices()
device = nd.find('arista-sw1')

handler = napalm.NapalmHandler(device)
handler.open()

facts = driver.get_facts()
"""

from __future__ import absolute_import

import napalm
from twisted.internet import defer, threads

from trigger.netdevices.handlers.base import BaseHandler


# Mapping of Trigger driver name => Napalm driver name
DRIVER_MAP = {
    'cisco': 'ios',
    'arista': 'eos',
    'juniper': 'junos',
}


class NapalmHandler(BaseHandler):
    name = 'napalm'

    def post_init(self):
        self.driver = self._get_driver_for_netdevice(self.device)
        self.napalm_device = self.driver(
            self.device.nodeName, self.creds.username, self.creds.password
        )

    def _get_driver_for_netdevice(self, device):
        vendor_name = device.vendor.name
        driver_name = DRIVER_MAP.get(vendor_name)

        return napalm.get_network_driver(driver_name)

    def perform_open(self, *args, **kwargs):
        self.napalm_device.open(*args, **kwargs)

    def perform_close(self):
        self.napalm_device.close()

    def get_facts(self):
        return self.napalm_device.get_facts()

    @defer.inlineCallbacks
    def get_facts_async(self):
        """
        Like get_facts but returns a Deferred.

        See:
            https://github.com/trigger/trigger/wiki/Trigger-2.0-Benchmarks#code-1
        """
        result = yield self.napalm_device.get_facts()
        defer.returnValue(result)

    @defer.inlineCallbacks
    def execute(self, commands=None):
        self.open()

        # This is just a simple proof-of-concept for executing commands directly
        # on an Arista EOS device using Napalm.
        result = yield threads.deferToThread(
            self.napalm_device.device.run_commands, commands, encoding='text'
        )
        defer.returnValue(result)
