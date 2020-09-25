"""
Napalm dispatcher.

Try me with:

#!/usr/bin/env python

import sys

from twisted.python import log
log.startLogging(open('/tmp/napalm_dispatcher_test.log', 'a+'), setStdout=False)

from trigger.netdevices import NetDevices

nd = NetDevices()
device = nd.find('arista-sw1')

device.open(dispatcher='napalm')

facts = device.dispatch('get_facts')
"""

from __future__ import absolute_import

from crochet import wait_for, run_in_reactor, setup; setup()
import napalm
from twisted.internet import defer, threads

from trigger.netdevices.dispatchers.base import BaseDispatcher


# Mapping of Trigger driver name => Napalm driver name
DRIVER_MAP = {
    'cisco': 'ios',
    'arista': 'eos',
    'juniper': 'junos',
}


class NapalmDispatcher(BaseDispatcher):

    def driver_connected(self):
        is_alive = self.driver.is_alive()
        return is_alive['is_alive']  # Nested like wutttttt

    def get_driver(self):
        vendor_name = self.device.vendor.name
        driver_name = DRIVER_MAP.get(vendor_name)

        napalm_driver = napalm.get_network_driver(driver_name)
        driver = napalm_driver(
            self.device.nodeName, self.creds.username, self.creds.password
        )
        return driver

    @defer.inlineCallbacks
    def dispatch(self, method_name, *args, **kwargs):
        """
        Like default dispatch, but explicitly returns a Deferred.
        See:
            https://github.com/trigger/trigger/wiki/Trigger-2.0-Benchmarks#code-1
        """
        driver = self.driver
        method = getattr(driver, method_name)

        print 'Calling %s on %s w/ args=%r, kwargs=%r' % (
            method_name, driver, args, kwargs
        )

        result = yield threads.deferToThread(method, *args, **kwargs)
        defer.returnValue(result)

    @defer.inlineCallbacks
    def execute(self, commands=None):
        self.dispatch('open')

        # This is just a simple proof-of-concept for executing commands directly
        # on an Arista EOS device using Napalm.
        result = yield threads.deferToThread(
            self.napalm_device.device.run_commands, commands, encoding='text'
        )
        defer.returnValue(result)
