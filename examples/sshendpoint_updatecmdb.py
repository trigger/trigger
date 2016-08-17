#!/usr/bin/env python

import sys
from time import sleep
from twisted.internet.defer import Deferred
from zope.interface import implements
from twisted.internet import reactor
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.internet.defer import succeed
from twisted.web.iweb import IBodyProducer
# from twisted.python import log
# log.startLogging(sys.stdout, setStdout=False)
from trigger.netdevices import NetDevices

# Create reference to upgraded switch.
nd = NetDevices()
dev = nd.find('arista-sw1.demo.local')

# Create payload body
class StringProducer(object):
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass

def update_cmdb(result, node):
    import re
    pattern = re.compile('Software image version: (4.12.0-1244667)')
    os = pattern.search(result[0]).group(1)

    agent = Agent(reactor)
    body = StringProducer("""
    {{'Devices':[
        {{Name:'{name}', OS:'{os}'}}
    ]}}""".format(name=node.nodeName, os=os).strip())
    d = agent.request(
        'GET',
        'http://192.168.1.194/',
        Headers({'User-Agent': ['Twisted Web Client Example'],
                 'Content-Type': ['application/json']}),
        body)

    def cbResponse(ignored):
        print 'Response received'
    d.addCallback(cbResponse)

# Open connection to device.
print "Begin example. Please wait while we extract the OS version from {name}'s show version output.".format(name=dev.nodeName)
dev.open()

# Pause due to timing inconsistencies experienced in some devices.
sleep(5)

# Execute some commands
r10 = dev.run_channeled_commands(['show version'])

# Perform update cmdb action based on the output of arista-sw1's show version.
r10.addCallback(update_cmdb, dev)
r10.addBoth(dev.close)
