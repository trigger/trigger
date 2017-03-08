# -*- coding: utf-8 -*-

"""
This module abstracts the asynchronous execution of commands on multiple
network devices. It allows for integrated parsing and event-handling of return
data for rapid integration to existing or newly-created tools.

The `~trigger.cmds.Commando` class is designed to be extended but can still be
used as-is to execute commands and return the results as-is.
"""

__author__ = 'Jathan McCollum, Eileen Tschetter, Mark Thomas'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan@gmail.com'
__copyright__ = 'Copyright 2009-2013, AOL Inc.; 2014 Salesforce.com'
__version__ = '2.7'


# Imports
import collections
import datetime
import itertools
import os
from IPy import IP
from xml.etree.cElementTree import ElementTree, Element, SubElement
import sys
from twisted.python import log
from twisted.internet import defer, task

from trigger.netdevices import NetDevices
from trigger.utils.templates import load_cmd_template, get_textfsm_object, get_template_path
from trigger.conf import settings
from trigger import exceptions


# Exports
__all__ = ('Commando', 'ReactorlessCommando', 'NetACLInfo')


# Default timeout in seconds for commands to return a result
DEFAULT_TIMEOUT = 30


# Classes
class Commando(object):
    """
    Execute commands asynchronously on multiple network devices.

    This class is designed to be extended but can still be used as-is to execute
    commands and return the results as-is.

    At the bare minimum you must specify a list of ``devices`` to interact with.
    You may optionally specify a list of ``commands`` to execute on those
    devices, but doing so will execute the same commands on every device
    regardless of platform.

    If ``commands`` are not specified, they will be expected to be emitted by
    the ``generate`` method for a given platform. Otherwise no commands will be
    executed.

    If you wish to customize the commands executed by device, you must define a
    ``to_{vendor_name}`` method containing your custom logic.

    If you wish to customize what is done with command results returned from a
    device, you must define a ``from_{vendor_name}`` method containing your
    custom logic.

    :param devices:
        A list of device hostnames or `~trigger.netdevices.NetDevice` objects

    :param commands:
        (Optional) A list of commands to execute on the ``devices``.

    :param creds:
        (Optional) A 3-tuple of (username, password, realm). If only (username,
        password) are provided, realm will be populated from
        :setting:`DEFAULT_REALM`. If unset it will fetch from ``.tacacsrc``.

    :param incremental:
        (Optional) A callback that will be called with an empty sequence upon
        connection and then called every time a result comes back from the
        device, with the list of all results.

    :param max_conns:
        (Optional) The maximum number of simultaneous connections to keep open.

    :param verbose:
        (Optional) Whether or not to display informational messages to the
        console.

    :param timeout:
        (Optional) Time in seconds to wait for each command executed to return a
        result. Set to ``None`` to disable timeout (not recommended).

    :param production_only:
        (Optional) If set, includes all devices instead of excluding any devices
        where ``adminStatus`` is not set to ``PRODUCTION``.

    :param allow_fallback:
        If set (default), allow fallback to base parse/generate methods when
        they are not customized in a subclass, otherwise an exception is raised
        when a method is called that has not been explicitly defined.

    :param with_errors:
        (Optional) Return exceptions as results instead of raising them. The
        default is to always return them.

    :param force_cli:
        (Optional) Juniper only. If set, sends commands using CLI instead of
        Junoscript.

    :param with_acls:
         Whether to load ACL associations (requires Redis). Defaults to whatever
         is specified in settings.WITH_ACLS

    :param command_interval:
         (Optional) Amount of time in seconds to wait between sending commands.

    :param stop_reactor:
         Whether to stop the reactor loop when all results have returned.
         (Default: ``True``)
    """
    # Defaults to all supported vendors
    vendors = settings.SUPPORTED_VENDORS

    # Defaults to all supported platforms
    platforms = settings.SUPPORTED_PLATFORMS

    # The commands to run (defaults to [])
    commands = None

    # The timeout for commands to return results. We are setting this to 0
    # so that if it's not overloaded in a subclass, the timeout value passed to
    # the constructor will be preferred, especially if it is set to ``None``
    # which Twisted uses to disable timeouts completely.
    timeout = 0

    # How results are stored (defaults to {})
    results = None

    # How parsed results are stored (defaults to {})
    parsed_results = None

    # How errors are stored (defaults to {})
    errors = None

    # Whether to stop the reactor when all results have returned.
    stop_reactor = None

    def __init__(self, devices=None, commands=None, creds=None,
                 incremental=None, max_conns=10, verbose=False,
                 timeout=DEFAULT_TIMEOUT, production_only=True,
                 allow_fallback=True, with_errors=True, force_cli=False,
                 with_acls=False, command_interval=0, stop_reactor=True):
        if devices is None:
            raise exceptions.ImproperlyConfigured('You must specify some `devices` to interact with!')

        self.devices = devices
        self.commands = self.commands or (commands or []) # Always fallback to []
        self.creds = creds
        self.incremental = incremental
        self.max_conns = max_conns
        self.verbose = verbose
        self.timeout = timeout if timeout != self.timeout else self.timeout
        self.nd = NetDevices(production_only=production_only, with_acls=with_acls)
        self.allow_fallback = allow_fallback
        self.with_errors = with_errors
        self.force_cli = force_cli
        self.command_interval = command_interval
        self.stop_reactor = self.stop_reactor or stop_reactor
        self.curr_conns = 0
        self.jobs = []

        # Always fallback to {} for these
        self.errors = self.errors if self.errors is not None else {}
        self.results = self.results if self.results is not None else {}
        self.parsed_results = self.parsed_results if self.parsed_results is not None else {}

        #self.deferrals = []
        self.supported_platforms = self._validate_platforms()
        self._setup_jobs()

    def _validate_platforms(self):
        """
        Determine the set of supported platforms for this instance by making
        sure the specified vendors/platforms for the class match up.
        """
        supported_platforms = {}
        for vendor in self.vendors:
            if vendor in self.platforms:
                types = self.platforms[vendor]
                if not types:
                    raise exceptions.MissingPlatform('No platforms specified for %r' % vendor)
                else:
                    #self.supported_platforms[vendor] = types
                    supported_platforms[vendor] = types
            else:
                raise exceptions.ImproperlyConfigured('Platforms for vendor %r not found. Please provide it at either the class level or using the arguments.' % vendor)

        return supported_platforms

    def _decrement_connections(self, data=None):
        """
        Self-explanatory. Called by _add_worker() as both callback/errback
        so we can accurately refill the jobs queue, which relies on the
        current connection count.
        """
        self.curr_conns -= 1
        return data

    def _increment_connections(self, data=None):
        """Increment connection count."""
        self.curr_conns += 1
        return True

    def _setup_jobs(self):
        """
        "Maps device hostnames to `~trigger.netdevices.NetDevice` objects and
        populates the job queue.
        """
        for dev in self.devices:
            log.msg('Adding', dev)
            if self.verbose:
                print 'Adding', dev

            # Make sure that devices are actually in netdevices and keep going
            try:
                devobj = self.nd.find(str(dev))
            except KeyError:
                msg = 'Device not found in NetDevices: %s' % dev
                log.err(msg)
                if self.verbose:
                    print 'ERROR:', msg

                # Track the errors and keep moving
                self.store_error(dev, msg)
                continue

            # We only want to add devices for which we've enabled support in
            # this class
            if devobj.vendor not in self.vendors:
                raise exceptions.UnsupportedVendor("The vendor '%s' is not specified in ``vendors``. Could not add %s to job queue. Please check the attribute in the class object." % (devobj.vendor, devobj))

            self.jobs.append(devobj)

    def select_next_device(self, jobs=None):
        """
        Select another device for the active queue.

        Currently only returns the next device in the job queue. This is
        abstracted out so that this behavior may be customized, such as for
        future support for incremental callbacks.

        If a device is determined to be invalid, you must return ``None``.

        :param jobs:
            (Optional) The jobs queue. If not set, uses ``self.jobs``.

        :returns:
            A `~trigger.netdevices.NetDevice` object or ``None``.
        """
        if jobs is None:
            jobs = self.jobs

        return jobs.pop()

    def _add_worker(self):
        """
        Adds devices to the work queue to keep it populated with the maximum
        connections as specified by ``max_conns``.
        """
        while self.jobs and self.curr_conns < self.max_conns:
            device = self.select_next_device()
            if device is None:
                log.msg('No device returned when adding worker. Moving on.')
                continue

            self._increment_connections()
            log.msg('connections:', self.curr_conns)
            log.msg('Adding work to queue...')
            if self.verbose:
                print 'connections:', self.curr_conns
                print 'Adding work to queue...'

            # Setup the async Deferred object with a timeout and error printing.
            commands = self.generate(device)
            async = device.execute(commands, creds=self.creds,
                                   incremental=self.incremental,
                                   timeout=self.timeout,
                                   with_errors=self.with_errors,
                                   force_cli=self.force_cli,
                                   command_interval=self.command_interval)

            # Add the template parser callback for great justice!
            async.addCallback(self.parse_template, device, commands)

            # Add the parser callback for even greater justice!
            async.addCallback(self.parse, device, commands)

            # If parse fails, still decrement and track the error
            async.addErrback(self.errback, device)

            # Make sure any further uncaught errors get logged
            async.addErrback(log.err)

            # Here we addBoth to continue on after pass/fail, decrement the
            # connections and move on.
            async.addBoth(self._decrement_connections)
            async.addBoth(lambda x: self._add_worker())

        # Do this once we've exhausted the job queue
        else:
            if not self.curr_conns and self.reactor_running:
                self._stop()
            elif not self.jobs and not self.reactor_running:
                log.msg('No work left.')
                if self.verbose:
                    print 'No work left.'

    def _lookup_method(self, device, method):
        """
        Base lookup method. Looks up stuff by device manufacturer like:

            from_juniper
            to_foundry

        and defaults to ``self.from_base`` and ``self.to_base`` methods if
        customized methods not found.

        :param device:
            A `~trigger.netdevices.NetDevice` object

        :param method:
            One of 'generate', 'parse'
        """
        METHOD_MAP = {
            'generate': 'to_%s',
            'parse': 'from_%s',
        }
        assert method in METHOD_MAP

        desired_method = None

        # Select the desired vendor name.
        desired_vendor = device.vendor.name

        # Workaround until we implement device drivers
        if device.is_netscreen():
            desired_vendor = 'netscreen'

        vendor_types = self.platforms.get(desired_vendor)
        method_name = METHOD_MAP[method] % desired_vendor  # => 'to_cisco'
        device_type = device.deviceType

        if device_type in vendor_types:
            if hasattr(self, method_name):
                log.msg(
                    '[%s] Found %r method: %s' % (device, method, method_name)
                )
                desired_method = method_name
            else:
                log.msg(
                    '[%s] Did not find %r method: %s' % (device, method,
                                                         method_name)
                )
        else:
            raise exceptions.UnsupportedDeviceType(
                'Device %r has an invalid type %r for vendor %r. Must be '
                'one of %r.' % (device.nodeName, device_type,
                                desired_vendor, vendor_types)
            )

        if desired_method is None:
            if self.allow_fallback:
                desired_method = METHOD_MAP[method] % 'base'
                log.msg('[%s] Fallback enabled. Using base method: %r' %
                        (device, desired_method))
            else:
                raise exceptions.UnsupportedVendor(
                    'The vendor %r had no available %s method. Please check '
                    'your `vendors` and `platforms` attributes in your class '
                    'object.' % (device.vendor.name, method)
                )

        func = getattr(self, desired_method)
        return func

    def generate(self, device, commands=None, extra=None):
        """
        Generate commands to be run on a device. If you don't provide
        ``commands`` to the class constructor, this will return an empty list.

        Define a 'to_{vendor_name}' method to customize the behavior for each
        platform.

        :param device:
            NetDevice object
        :type device:
            `~trigger.netdevices.NetDevice`

        :param commands:
            (Optional) A list of commands to execute on the device. If not
            specified in they will be inherited from commands passed to the
            class constructor.
        :type commands:
            list

        :param extra:
            (Optional) A dictionary of extra data to send to the generate
            method for the device.
        """
        if commands is None:
            commands = self.commands
        if extra is None:
            extra = {}

        func = self._lookup_method(device, method='generate')
        return func(device, commands, extra)

    def parse_template(self, results, device, commands=None):
        """
        Generator function that processes unstructured CLI data and yields either
        a TextFSM based object or generic raw output.

        :param results:
            The unstructured "raw" CLI data from device.
        :type  results:
            str
        :param device:
            NetDevice object
        :type device:
            `~trigger.netdevices.NetDevice`
        """

        device_type = device.os
        ret = []

        for idx, command in enumerate(commands):
            if device_type:
                try:
                    re_table = load_cmd_template(command, dev_type=device_type)
                    fsm = get_textfsm_object(re_table, results[idx])
                    self.append_parsed_results(device, self.map_parsed_results(command, fsm))
                except:
                    log.msg("Unable to load TextFSM template, just updating with unstructured output")

            ret.append(results[idx])

        return ret

    def parse(self, results, device, commands=None):
        """
        Parse output from a device. Calls to ``self._lookup_method`` to find
        specific ``from`` method.

        Define a 'from_{vendor_name}' method to customize the behavior for each
        platform.

        :param results:
            The results of the commands executed on the device
        :type results:
            list

        :param device:
            Device object
        :type device:
            `~trigger.netdevices.NetDevice`

        :param commands:
            (Optional) A list of commands to execute on the device. If not
            specified in they will be inherited from commands passed to the
            class constructor.
        :type commands:
            list
        """
        func = self._lookup_method(device, method='parse')
        return func(results, device, commands)

    def errback(self, failure, device):
        """
        The default errback. Overload for custom behavior but make sure it
        always decrements the connections.

        :param failure:
            Usually a Twisted ``Failure`` instance.

        :param device:
            A `~trigger.netdevices.NetDevice` object
        """
        failure.trap(Exception)
        self.store_error(device, failure)
        #self._decrement_connections(failure)
        return failure

    def store_error(self, device, error):
        """
        A simple method for storing an error called by all default
        parse/generate methods.

        If you want to customize the default method for storing results,
        overload this in your subclass.

        :param device:
            A `~trigger.netdevices.NetDevice` object

        :param error:
            The error to store. Anything you want really, but usually a Twisted
            ``Failure`` instance.
        """
        devname = str(device)
        self.errors[devname] = error
        return True

    def append_parsed_results(self, device, results):
        """
        A simple method for appending results called by template parser
        method.

        If you want to customize the default method for storing parsed
        results, overload this in your subclass.

        :param device:
            A `~trigger.netdevices.NetDevice` object

        :param results:
            The results to store. Anything you want really.
        """
        devname = str(device)
        log.msg("Appending results for %r: %r" % (devname, results))
        if self.parsed_results.get(devname):
            self.parsed_results[devname].update(results)
        else:
            self.parsed_results[devname] = results
        return True

    def store_results(self, device, results):
        """
        A simple method for storing results called by all default
        parse/generate methods.

        If you want to customize the default method for storing results,
        overload this in your subclass.

        :param device:
            A `~trigger.netdevices.NetDevice` object

        :param results:
            The results to store. Anything you want really.
        """
        devname = str(device)
        log.msg("Storing results for %r: %r" % (devname, results))
        self.results[devname] = results
        return True

    def map_parsed_results(self, command=None, fsm=None):
        """Return a dict of ``{command: fsm, ...}``"""
        if fsm is None:
            fsm = {}

        return {command: fsm}

    def map_results(self, commands=None, results=None):
        """Return a dict of ``{command: result, ...}``"""
        if commands is None:
            commands = self.commands
        if results is None:
            results = []

        return dict(itertools.izip_longest(commands, results))

    @property
    def reactor_running(self):
        """Return whether reactor event loop is running or not"""
        from twisted.internet import reactor
        log.msg("Reactor running? %s" % reactor.running)
        return reactor.running

    def _stop(self):
        """Stop the reactor event loop"""

        if self.stop_reactor:
            log.msg('Stop reactor enabled: stopping reactor...')
            from twisted.internet import reactor
            if reactor.running:
                reactor.stop()
        else:
            log.msg('stopping reactor... except not really.')
            if self.verbose:
                print 'stopping reactor... except not really.'

    def _start(self):
        """Start the reactor event loop"""
        log.msg('starting reactor. maybe.')
        if self.verbose:
            print 'starting reactor. maybe.'

        if self.curr_conns:
            from twisted.internet import reactor
            if not reactor.running:
                reactor.run()
        else:
            msg = "Won't start reactor with no work to do!"
            log.msg(msg)
            if self.verbose:
                print msg

    def run(self):
        """
        Nothing happens until you execute this to perform the actual work.
        """
        self._add_worker()
        self._start()

    #=======================================
    # Base generate (to_)/parse (from_) methods
    #=======================================
    def to_base(self, device, commands=None, extra=None):
        commands = commands or self.commands
        log.msg('Sending %r to %s' % (commands, device))
        return commands

    def from_base(self, results, device, commands=None):
        commands = commands or self.commands
        log.msg('Received %r from %s' % (results, device))
        self.store_results(device, self.map_results(commands, results))

    #=======================================
    # Vendor-specific generate (to_)/parse (from_) methods
    #=======================================
    def to_juniper(self, device, commands=None, extra=None):
        """
        This just creates a series of ``<command>foo</command>`` elements to
        pass along to execute_junoscript()"""
        commands = commands or self.commands

        # If we've set force_cli, use to_base() instead
        if self.force_cli:
            return self.to_base(device, commands, extra)

        ret = []
        for command in commands:
            cmd = Element('command')
            cmd.text = command
            ret.append(cmd)

        return ret


class ReactorlessCommando(Commando):
    """
    A reactor-less Commando subclass.

    This allows multiple instances to coexist, with the side-effect that you
    have to manage the reactor start/stop manually.

    An example of how this could be used::

        from twisted.internet import defer, reactor

        devices = ['dev1', 'dev2']

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
        d.addBoth(lambda _: reactor.stop())

        # And... finally, start the reactor to kick things off.
        reactor.run()

        # Inspect your results
        print d.result
    """
    def _start(self):
        """Initializes ``all_done`` instead of starting the reactor"""
        log.msg("._start() called")
        self.all_done = False

    def _stop(self):
        """Sets ``all_done`` to True instead of stopping the reactor"""
        log.msg("._stop() called")
        self.all_done = True

    def run(self):
        """
        We've overloaded the run method to return a Deferred task object.
        """
        log.msg(".run() called")

        # This is the default behavior
        super(ReactorlessCommando, self).run()

        # Setup a deferred to hold the delayed result and not return it until
        # it's done. This object will be populated with the value of the
        # results once all commands have been executed on all devices.
        d = defer.Deferred()

        # Add monitor_result as a callback
        from twisted.internet import reactor
        d.addCallback(self.monitor_result, reactor)

        # Tell the reactor to call the callback above when it starts
        reactor.callWhenRunning(d.callback, reactor)

        return d

    def monitor_result(self, result, reactor):
        """
        Loop periodically or until the factory stops to check if we're
        ``all_done`` and then return the results.
        """
        # Once we're done, return the results
        if self.all_done:
            return self.results

        # Otherwise tell the reactor to call me again after 0.5 seconds.
        return task.deferLater(reactor, 0.5, self.monitor_result, result, reactor)



class NetACLInfo(Commando):
    """
    Class to fetch and parse interface information. Exposes a config
    attribute which is a dictionary of devices passed to the constructor and
    their interface information.

    Each device is a dictionary of interfaces. Each interface field will
    default to an empty list if not populated after parsing.  Below is a
    skeleton of the basic config, with expected fields::

        config {
            'device1': {
                'interface1': {
                    'acl_in': [],
                    'acl_out': [],
                    'addr': [],
                    'description': [],
                    'subnets': [],
                }
            }
        }

    Interface field descriptions:

        :addr:
            List of ``IPy.IP`` objects of interface addresses

        :acl_in:
            List of inbound ACL names

        :acl_out:
            List of outbound ACL names

        :description:
            List of interface description(s)

        :subnets:
            List of ``IPy.IP`` objects of interface networks/CIDRs

    Example::

        >>> n = NetACLInfo(devices=['jm10-cc101-lab.lab.aol.net'])
        >>> n.run()
        Fetching jm10-cc101-lab.lab.aol.net
        >>> n.config.keys()
        [<NetDevice: jm10-cc101-lab.lab.aol.net>]
        >>> dev = n.config.keys()[0]
        >>> n.config[dev].keys()
        ['lo0.0', 'ge-0/0/0.0', 'ge-0/2/0.0', 'ge-0/1/0.0', 'fxp0.0']
        >>> n.config[dev]['lo0.0'].keys()
        ['acl_in', 'subnets', 'addr', 'acl_out', 'description']
        >>> lo0 = n.config[dev]['lo0.0']
        >>> lo0['acl_in']; lo0['addr']
        ['abc123']
        [IP('66.185.128.160')]

    This accepts all arguments from the `~trigger.cmds.Commando` parent class,
    as well as this one extra:

    :param skip_disabled:
        Whether to include interface names without any information. (Default:
        ``True``)
    """
    def __init__(self, **args):
        try:
            import pyparsing as pp
        except ImportError:
            raise RuntimeError("You must install ``pyparsing==1.5.7`` to use NetACLInfo")
        self.config = {}
        self.skip_disabled = args.pop('skip_disabled', True)
        super(NetACLInfo, self).__init__(**args)

    def IPsubnet(self, addr):
        '''Given '172.20.1.4/24', return IP('172.20.1.0/24').'''
        return IP(addr, make_net=True)

    def IPhost(self, addr):
        '''Given '172.20.1.4/24', return IP('172.20.1.4/32').'''
        return IP(addr[:addr.index('/')]) # Only keep before "/"

    #=======================================
    # Vendor-specific generate (to_)/parse (from_) methods
    #=======================================

    def to_cisco(self, dev, commands=None, extra=None):
        """This is the "show me all interface information" command we pass to
        IOS devices"""
        if dev.is_cisco_asa():
            return ['show running-config | include ^(interface | ip address | nameif | description |access-group|!)']
        elif dev.is_cisco_nexus():
            return ['show running-config | include "^(interface |  ip address |  ip access-group |  description |!)"']
        else:
            return ['show configuration | include ^(interface | ip address | ip access-group | description|!)']

    def to_arista(self, dev, commands=None, extra=None):
        """
        Similar to IOS, but:

           + Arista has no "show conf" so we have to do "show run"
           + The regex used in the CLI for Arista is more "precise" so we have
             to change the pattern a little bit compared to the on in
             generate_ios_cmd

        """
        return ['show running-config | include (^interface | ip address | ip access-group | description |!)']

    def to_force10(self, dev, commands=None, extra=None):
        """
        Similar to IOS, but:
            + You only get the "grep" ("include" equivalent) when using "show
              run".
            + The regex must be quoted.
        """
        return ['show running-config | grep "^(interface | ip address | ip access-group | description|!)"']

    # Other IOS-like vendors are Cisco-enough
    to_brocade = to_cisco
    to_foundry = to_cisco

    def from_cisco(self, data, device, commands=None):
        """Parse IOS config based on EBNF grammar"""
        self.results[device.nodeName] = data #"MY OWN IOS DATA"
        alld = data[0]

        log.msg('Parsing interface data (%d bytes)' % len(alld))
        if not device.is_cisco_asa():
            self.config[device] = _parse_ios_interfaces(alld, skip_disabled=self.skip_disabled)
        else:
            self.config[device] = {
                "unsupported": "ASA ACL parsing unsupported this release"
            }

        return True

    # Other IOS-like vendors are Cisco-enough
    from_arista = from_cisco
    from_brocade = from_cisco
    from_foundry = from_cisco
    from_force10 = from_cisco

    def to_juniper(self, dev, commands=None, extra=None):
        """Generates an etree.Element object suitable for use with
        JunoScript"""
        cmd = Element('get-configuration',
            database='committed',
            inherit='inherit')

        SubElement(SubElement(cmd, 'configuration'), 'interfaces')

        self.commands = [cmd]
        return self.commands

    def __children_with_namespace(self, ns):
        return lambda elt, tag: elt.findall('./' + ns + tag)

    def from_juniper(self, data, device, commands=None):
        """Do all the magic to parse Junos interfaces"""
        self.results[device.nodeName] = data #"MY OWN JUNOS DATA"

        ns = '{http://xml.juniper.net/xnm/1.1/xnm}'
        children = self.__children_with_namespace(ns)

        xml = data[0]
        dta = {}
        for interface in xml.getiterator(ns + 'interface'):

            basename = children(interface, 'name')[0].text

            description = interface.find(ns + 'description')
            desctext = []
            if description is not None:
                desctext.append(description.text)

            for unit in children(interface, 'unit'):
                ifname = basename + '.' + children(unit, 'name')[0].text
                dta[ifname] = {}
                dta[ifname]['addr'] = []
                dta[ifname]['subnets'] = []
                dta[ifname]['description'] = desctext
                dta[ifname]['acl_in'] = []
                dta[ifname]['acl_out'] = []

                # Iterating the "family/inet" tree. Seems ugly.
                for family in children(unit, 'family'):
                    for family2 in family:
                        if family2.tag != ns + 'inet':
                            continue
                        for inout in 'in', 'out':
                            dta[ifname]['acl_%s' % inout] = []

                            # Try basic 'filter/xput'...
                            acl = family2.find('%sfilter/%s%sput' % (ns, ns, inout))

                            # Junos 9.x changes to 'filter/xput/filter-name'
                            if acl is not None and "    " in acl.text:
                                 acl = family2.find('%sfilter/%s%sput/%sfilter-name' % (ns, ns, inout, ns))

                            # Pushes text as variable name.  Must be a better way to do this?
                            if acl is not None:
                                acl = acl.text

                            # If we couldn't match a single acl, try 'filter/xput-list'
                            if not acl:
                                #print 'trying filter list..'
                                acl = [i.text for i in family2.findall('%sfilter/%s%sput-list' % (ns, ns, inout))]
                                #if acl: print 'got filter list'

                            # Otherwise, making single acl into a list
                            else:
                                acl = [acl]

                            # Append acl list to dict
                            if acl:
                                dta[ifname]['acl_%s' % inout].extend(acl)

                        for node in family2.findall('%saddress/%sname' % (ns, ns)):
                            ip = node.text
                            dta[ifname]['subnets'].append(self.IPsubnet(ip))
                            dta[ifname]['addr'].append(self.IPhost(ip))

        self.config[device] = dta
        return True


def _parse_ios_interfaces(data, acls_as_list=True, auto_cleanup=True, skip_disabled=True):
    """
    Walks through a IOS interface config and returns a dict of parts.

    Intended for use by `~trigger.cmds.NetACLInfo.ios_parse()` but was written
    to be portable.

    :param acls_as_list:
        Whether you want acl names as strings instead of list members, e.g.

    :param auto_cleanup:
        Whether you want to pass results through cleanup_results(). Default: ``True``)
        "ABC123" vs. ['ABC123']. (Default: ``True``)

    :param skip_disabled:
        Whether to skip disabled interfaces. (Default: ``True``)
    """
    import pyparsing as pp

    # Setup
    bang = pp.Literal("!").suppress()
    anychar = pp.Word(pp.printables)
    nonbang = pp.Word(''.join([x for x in pp.printables if x != "!"]) + '\n\r\t ')
    comment = bang + pp.restOfLine.suppress()

    #weird things to ignore in foundries
    aaa_line = pp.Literal("aaa").suppress() + pp.restOfLine.suppress()
    module_line = pp.Literal("module").suppress() + pp.restOfLine.suppress()
    startup_line = pp.Literal("Startup").suppress() + pp.restOfLine.suppress()
    ver_line = pp.Literal("ver") + anychar#+ pp.restOfLine.suppress()
    #using SkipTO instead now

    #foundry example:
    #telnet@olse1-dc5#show  configuration | include ^(interface | ip address | ip access-group | description|!)
    #!
    #Startup-config data location is flash memory
    #!
    #Startup configuration:
    #!
    #ver 07.5.05hT53
    #!
    #module 1 bi-0-port-m4-management-module
    #module 2 bi-8-port-gig-module

    #there is a lot more that foundry is including in the output that should be ignored

    interface_keyword = pp.Keyword("interface")
    unwanted = pp.SkipTo(interface_keyword, include=False).suppress()

    #unwanted = pp.ZeroOrMore(bang ^ comment ^ aaa_line ^ module_line ^ startup_line ^ ver_line)

    octet = pp.Word(pp.nums, max=3)
    ipaddr = pp.Combine(octet + "." + octet + "." + octet + "." + octet)
    address = ipaddr
    netmask = ipaddr
    cidr = pp.Literal("/").suppress() + pp.Word(pp.nums, max=2)

    # Description
    desc_keyword = pp.Keyword("description")
    description = pp.Dict( pp.Group(desc_keyword + pp.Group(pp.restOfLine)) )

    # Addresses
    #cisco example:
    # ip address 172.29.188.27 255.255.255.224 secondary
    #
    #foundry example:
    # ip address 10.62.161.187/26

    ipaddr_keyword = pp.Keyword("ip address").suppress()
    secondary = pp.Literal("secondary").suppress()

    #foundry matches on cidr and cisco matches on netmask
    #netmask converted to cidr in cleanup
    ip_tuple = pp.Group(address + (cidr ^ netmask)).setResultsName('addr', listAllMatches=True)
    negotiated = pp.Literal('negotiated')  # Seen on Cisco 886
    ip_address = ipaddr_keyword + (negotiated ^ ip_tuple) + pp.Optional(secondary)

    addrs = pp.ZeroOrMore(ip_address)

    # ACLs
    acl_keyword = pp.Keyword("ip access-group").suppress()

    # acl_name to be [''] or '' depending on acls_as_list
    acl_name = pp.Group(anychar) if acls_as_list else anychar
    direction = pp.oneOf('in out').suppress()
    acl_in = acl_keyword + pp.FollowedBy(acl_name + pp.Literal('in'))
    acl_in.setParseAction(pp.replaceWith('acl_in'))
    acl_out = acl_keyword + pp.FollowedBy(acl_name + pp.Literal('out'))
    acl_out.setParseAction(pp.replaceWith('acl_out'))

    acl = pp.Dict( pp.Group((acl_in ^ acl_out) + acl_name)) + direction
    acls = pp.ZeroOrMore(acl)

    # Interfaces
    iface_keyword = pp.Keyword("interface").suppress()
    foundry_awesome = pp.Literal(" ").suppress() + anychar
    #foundry exmaple:
    #!
    #interface ethernet 6/6
    # ip access-group 126 in
    # ip address 172.18.48.187 255.255.255.255

    #cisco example:
    #!
    #interface Port-channel1
    # description gear1-mtc : AE1 : iwslbfa1-mtc-sw0 :  : 1x1000 : 172.20.166.0/24 :  :  :
    # ip address 172.20.166.251 255.255.255.0


    interface = pp.Combine(anychar + pp.Optional(foundry_awesome))

    iface_body = pp.Optional(description) + pp.Optional(acls) + pp.Optional(addrs) + pp.Optional(acls)
    #foundry's body is acl then ip and cisco's is ip then acl

    iface_info = pp.Optional(unwanted) + iface_keyword +  pp.Dict( pp.Group(interface + iface_body) ) + pp.Optional( pp.SkipTo(bang) )

    interfaces = pp.Dict( pp.ZeroOrMore(iface_info) )

    # This is where the parsing is actually happening
    try:
        results = interfaces.parseString(data)
    except: # (ParseException, ParseFatalException, RecursiveGrammarException):
        results = {}

    if auto_cleanup:
        return _cleanup_interface_results(results, skip_disabled=skip_disabled)
    return results


def _cleanup_interface_results(results, skip_disabled=True):
    """
    Takes ParseResults dictionary-like object and returns an actual dict of
    populated interface details.  The following is performed:

        * Ensures all expected fields are populated
        * Down/un-addressed interfaces are skipped
        * Bare IP/CIDR addresses are converted to IPy.IP objects

    :param results:
        Interface results to parse

    :param skip_disabled:
        Whether to skip disabled interfaces. (Default: ``True``)
    """
    interfaces = sorted(results.keys())
    newdict = {}
    for interface in interfaces:
        iface_info = results[interface]

        # Maybe skip down interfaces
        if 'addr' not in iface_info and skip_disabled:
            continue

        # Ensure we have a dict to work with.
        if not iface_info:
            iface_info = collections.defaultdict(list)

        newdict[interface] = {}
        new_int = newdict[interface]

        new_int['addr'] = _make_ipy(iface_info.get('addr', []))
        new_int['subnets'] = _make_cidrs(iface_info.get('subnets', iface_info.get('addr', [])))
        new_int['acl_in'] = list(iface_info.get('acl_in', []))
        new_int['acl_out'] = list(iface_info.get('acl_out', []))
        new_int['description'] = list(iface_info.get('description', []))

    return newdict


def _make_ipy(nets):
    """Given a list of 2-tuples of (address, netmask), returns a list of
    IP address objects"""
    return [IP(addr) for addr, mask in nets]


def _make_cidrs(nets):
    """Given a list of 2-tuples of (address, netmask), returns a list CIDR
    blocks"""
    return [IP(addr).make_net(mask) for addr, mask in nets]


def _dump_interfaces(idict):
    """Prints a dict of parsed interface results info for use in debugging"""
    for name, info in idict.items():
        print '>>>', name
        print '\t',
        if idict[name]:
            if hasattr(info, 'keys'):
                keys = info.keys()
                print keys
                for key in keys:
                    print '\t', key, ':', info[key]
            else:
                print str(info)
        else:
            print 'might be shutdown'
        print
