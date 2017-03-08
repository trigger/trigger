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
class Commando2(object):
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
            async = device.driver.execute(commands)

            # Add the template parser callback for great justice!
            #async.addCallback(self.parse_template, device, commands)

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
            async.addBoth(lambda x: device.driver.close())

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

        return results
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
