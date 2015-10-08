#!/usr/bin/env python

import sys
import jsonpickle
from trigger.cmds import ReactorlessCommando
from twisted.python import log
from twisted.internet import reactor
from Router import Router
from datetime import datetime


class getRouterDetails(ReactorlessCommando):
    commands = Router.showCommands

    def select_next_device(self, jobs=None):
        """
        Select another *reachable* device.
        """
        if jobs is None:
            jobs = self.jobs

        next_device = jobs.pop()
        log.msg('Selecting next device: %s' % next_device)

        # If I ping, return me.
        if next_device.is_reachable():
            log.msg('PING [SUCCESS]: %s' % next_device)
            return next_device
        # Otherwise return None and store me as an error.
        else:
            msg = 'PING [FAILURE]: %s' % next_device
            log.msg(msg)
            print "Failed to ping host {}".format(next_device)
            if self.verbose:
                print msg
            return None

    def errback(self, failure, device):
        print "Error in getRouterDetails for device {}\n{}".format(
            device,
            failure.getTraceback()
        )


def validateRouterDetails(result):
    devicesToCorrect = []

    for device, results in result.items():
        routers[device].results = results
        routers[device].validate()

    return None


def stop_reactor(result):
    if reactor.running:
        reactor.stop()
        return result


def main():
    # nd = NetDevices()

    global device_list
    device_list = []
    global routers
    routers = {}

    if len(sys.argv) > 1:
        device_list = sys.argv[1:]
    else:
        print "Processing all sites"
        with open('test-units.csv', 'rb') as csvfile:
            spamreader = csv.reader(csvfile, delimiter=',', quotechar='"')
            for row in spamreader:
                device_list.append(row[0])

    device_list = map(lambda x: x.lower(), device_list)

    try:
        stateFile = open("routerstate.json", "r")
        data = stateFile.read()
        stateFile.close()
        routers = jsonpickle.decode(data)
        data = None
    except Exception:
        print("Failed to open routerstate.json")

    for device in device_list:
        if device not in routers:
            routers[device] = Router(device)

    # log.startLogging(sys.stdout, setStdout=False)

    d = getRouterDetails(device_list, timeout=120, max_conns=30).run()
    d.addCallback(validateRouterDetails)
    d.addBoth(stop_reactor)

    reactor.run()

    with open('report.csv', 'w') as report:
        report.write("Device,Last Access,Version\n")

        for device in sorted(routers):
            reportLine = device
            if routers[device].lastAccess:
                reportLine += ",{:%Y-%m-%d %H:%M}".format(
                    routers[device].lastAccess
                )
            else:
                reportLine += ",Never"
            if routers[device].version:
                reportLine += "," + routers[device].version
            else:
                reportLine += ",Unknown"
            report.write(reportLine+"\n")

    stateFile = open("routerstate.json", "w")
    jsonpickle.set_encoder_options('json', sort_keys=True, indent=4)
    data = jsonpickle.encode(routers)
    stateFile.write(data)

if __name__ == '__main__':
    main()
