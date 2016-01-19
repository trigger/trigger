#!/usr/bin/env python

import sys
import csv
from trigger.cmds import ReactorlessCommando
from twisted.python import log
from twisted.internet import reactor
from Router import Router
import jsonpickle


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
    getRouterDetails, if a device requires normalization return it for
    processing by normalizeRouters
    """
    print "Validating router details"
    devicesToCorrect = []

    for device, results in result.items():
        routers[device].results = results
        routers[device].validate()
        routers[device].normalize()
        if routers[device].normalizeRequired:
            devicesToCorrect.append(device)

    return devicesToCorrect or None


class normalizeRouters(ReactorlessCommando):
    """
    Execute the normalization command list generated for each device
    """
    def to_cisco(self, dev, commands=None, extra=None):
        dev_commands = routers[dev.nodeName].commands
        return dev_commands

    def from_cisco(self, results, device, commands=None):
        commands = commands or self.commands

        log.msg('Received %r from %s' % (results, device))
        self.store_results(device, self.map_results(commands, results))

    def errback(self, failure, device):
        print "Error in normalizeRouters for device {}\n{}".format(
            device,
            failure.getTraceback()
        )


def initiateRouterNormalization(devices):
    """
    Call normalizeRouters with the devices that require normalization
    """
    if devices is not None:
        print "Normalizing {} devices ({})".format(
            len(devices),
            " ".join(devices)
        )
        devicesToNormalize = []
        for device in devices:
            if routers[device].normalizeRequired:
                devicesToNormalize.append(device)
        return normalizeRouters(devicesToNormalize).run()
    else:
        print "No devices need to be normalized".format()
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
    Collect data from devices and normalize their configuration if required
    """
    global device_list
    device_list = []
    global routers
    routers = {}

    try:
        stateFile = open("routerstate.json", "r")
        data = stateFile.read()
        stateFile.close()
        routers = jsonpickle.decode(data)
        data = None
    except Exception:
        print("Failed to open routerstate.json")

    # Accept a list of routers and argument or parse test-units.csv
    if len(sys.argv) > 1:
        device_list = sys.argv[1:]
    else:
        print "Processing all sites"
        with open('test-units.csv', 'rb') as csvfile:
            spamreader = csv.reader(csvfile, delimiter=',', quotechar='"')
            for row in spamreader:
                device_list.append(row[0])
        user_response = raw_input(
            "Are you certain you want to normalize {} devices? [y/N]\n".format(
                len(device_list)
            )
        )
        m = re.search("^[yY]", user_response)
        if m is None:
            print "Aborting processing"
            exit(1)

    device_list = map(lambda x: x.lower(), device_list)

    print "Processing {} devices ({})".format(
        len(device_list),
        " ".join(device_list)
    )

    for device in device_list:
        if device not in routers:
            routers[device] = Router(device)

    # log.startLogging(sys.stdout, setStdout=False)

    d = getRouterDetails(device_list).run()
    d.addCallback(validateRouterDetails)
    d.addCallback(initiateRouterNormalization)
    d.addBoth(stop_reactor)

    reactor.run()

    if d.result is not None:
        for device in d.result.keys():
            m = re.search(r"\[OK\]", d.result[device]["write mem"])
            if m is not None:
                print "Device {}: Configuration Saved".format(device)
            else:
                print "Device {}: Warning no [OK] in Output".format(device)

    stateFile = open("routerstate.json", "w")
    jsonpickle.set_encoder_options('json', sort_keys=True, indent=4)
    data = jsonpickle.encode(routers)
    stateFile.write(data)

if __name__ == '__main__':
    main()
