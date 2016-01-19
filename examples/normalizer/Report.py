#!/usr/bin/env python

import sys
import jsonpickle
import csv
from trigger.cmds import ReactorlessCommando
from twisted.python import log
from twisted.internet import reactor
from Router import Router
from datetime import datetime


class getRouterDetails(ReactorlessCommando):
    """
    Collection device information
    """
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
        """
        Error Handler for errors in getRouterDetails
        """
        print "Error in getRouterDetails for device {}\n{}".format(
            device,
            failure.getTraceback()
        )


def validateRouterDetails(result):
    """
    Runs device validations on each Router object that is returned by
    getRouterDetails
    """
    for device, results in result.items():
        routers[device].results = results
        routers[device].validate()

    return None


def stop_reactor(result):
    """
    Stop the reactor after execution
    """
    if reactor.running:
        reactor.stop()
        return result


def main():
    """
    Collect data from devices and generate the report
    """
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


    with open("report.csv", "w") as f:
        fieldNames = ["Device", "Last Access", "Version"]
        writer = csv.DictWriter(f, fieldNames)
        writer.writeheader()
    
        for router in routers.itervalues():
            try:
                last_access = "{:%Y-%m-%d %H:%M}".format(router.lastAccess)
            except AttributeError:
                last_access = "Never"
            try:
                version = router.version
            except AttributeError:
                version = "Unknown"
            writer.writerow({
                "Device": router.name,
                "Last Access": last_access,
                "Version": version
                })

    stateFile = open("routerstate.json", "w")
    jsonpickle.set_encoder_options('json', sort_keys=True, indent=4)
    data = jsonpickle.encode(routers)
    stateFile.write(data)

if __name__ == '__main__':
    main()
