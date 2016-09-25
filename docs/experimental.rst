############
Experimental
############

This document describes experimental currently in development as part of the Trigger re-architecture.

Asynchronous Endpoint Feature
=============================

`~trigger.netdevices.NetDevice` objects now contain interface methods for connect and command execution.
This is in contrast to traditional trigger whereby interaction with a given device is not re-entrant.

The following is a breakdown of these new API structures see ``examples/sshendpoint_updatecmdb.py`` at project root for more details.

Preamble
========

The code below defines two functions.

1. `StringProducer` is an ADT for the data that will be POST'd by the Twisted http client.
2. `update_cmdb` is a callback function that will be fired upon the return of `show version` on the remote endpoint.
   The purpose of this function is to POST the current IOS version into a CMDB system.

::

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



Code
====

Below details the code needed to actually run the command on the device and process the results asynchronously.

:: 

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


As you can be observed, we can continue to make asynchronous calls without having to restart the running process. With this in mind we could perform an action if the device
is not running on our minimum baseline version. This could be achieved like so:

:: 


        # Open connection to device.
        print "Begin example. Please wait while we extract the OS version from {name}'s show version output.".format(name=dev.nodeName)
        dev.open()

        def update_device(result, node):
            import re
            pattern = re.compile('Software image version: (4.12.0)')
            os = int(pattern.search(result[0]).group(1))

            # If OS is not at baseline, copy latest code to flash
            if os < 4.12.0:
                r10.dev.run_channeled_commands(['copy tftp://192.168.1.1/my-os.code flash: /md5', 'config t', 'boot system flash:my-os.code'])

        # Pause due to timing inconsistencies experienced in some devices.
        sleep(5)

        # Execute some commands
        r10 = dev.run_channeled_commands(['show version'])

        # Perform update cmdb action based on the output of arista-sw1's show version.
        r10.addCallback(update_device, dev)
        r10.addBoth(dev.close)


This is a contrived example, if doing something like this in product it is recommended to take the output of the md5 hash and compare it to a pre-compiled value associated with the file sitting on the tftp server.
