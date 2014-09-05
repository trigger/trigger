#!/usr/bin/env python

"""
commando_reactorless.py - Running multiple Commando's in the same script
"""

from trigger.cmds import ReactorlessCommando
from twisted.internet import defer, reactor
from twisted.python import log
import sys

# Uncomment me for verbose logging.
#log.startLogging(sys.stdout, setStdout=False)

class ShowClock(ReactorlessCommando):
    commands = ['show clock']

class ShowUsers(ReactorlessCommando):
    commands = ['show users']

def stop_reactor(result):
    if reactor.running:
        log.msg('STOPPING REACTOR!')
        reactor.stop()
    return result

if __name__ == '__main__':
    # Replace these with real device IPs/hostnames in your network
    devices = [
        'dev1',
        'dev2',
    ]

    # Our Commando instances. This is an example  to show we have two instances
    # co-existing under the same reactor.
    c1 = ShowClock(devices)
    c2 = ShowUsers(devices)
    instances = [c1, c2]

    # Call the run method for each instance to get a list of Deferred task objects.
    deferreds = []
    for i in instances:
        deferreds.append(i.run())

    # Here we use a DeferredList to track a list of Deferred tasks that only
    # returns once they've all completed.
    d = defer.DeferredList(deferreds)

    # Once every task has returned a result, stop the reactor
    d.addBoth(stop_reactor)

    # And... finally, start the reactor to kick things off.
    reactor.run()
