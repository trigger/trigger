"""
trigger.contrib.commando
~~~~~~~~~~~~~~~~~~~~~~~~

Simple command running for Trigger meant to be used with a
long-running reactor loop (such using the Twisted XMLRPC server).

This differs from `~trigger.cmds.Commando` in that:

+ It does not start/stop the reactor, instead it uses sentinel values and a
  task monitor to detect when it's done.
+ The ``.run()`` method returns a ``twisted.internet.defer.Deferred`` object.
+ Results/errors are stored in a list instead of a dict.
+ Each result object is meant to be easily serialized (e.g. to JSON).
"""

__author__ = 'Jathan McCollum, Mike Biancaniello'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan@gmail.com'
__copyright__ = 'Copyright 2012-2013, AOL Inc.'
__version__ = '0.2.1'


# Imports
import itertools
import cPickle as pickle
import os
from twisted.python import log, failure
from trigger.cmds import Commando
from trigger import exceptions
from twisted.internet import defer, task
import xml.etree.ElementTree as ET
from xml.etree.cElementTree import Element


# Exports
__all__ = ('CommandoApplication',)


# Enable Deferred debuging if ``DEBUG`` is set.
if os.getenv('DEBUG'):
    defer.setDebugging(True)


# Classes
class CommandoApplication(Commando):
    """
    Commando subclass to be used in an application where the reactor is always
    running (e.g. twistd or an application server).

    Stores results as a list of dictionaries ideal for serializing to JSON.
    """
    timeout = 5

    def __init__(self, *args, **kwargs):
        self.all_done = False
        self.results = []
        self.errors = []
        super(CommandoApplication, self).__init__(*args, **kwargs)

        if not self.devices:
            raise exceptions.ImproperlyConfigured('You must specify some `devices` to interact with!')
        # Commenting out because sometimes the cmds come in the to_<vendor> methods
        #if not self.commands:
        #    raise exceptions.ImproperlyConfigured('You must specify some `commands` to execute!')

        # Make sure that the specified containers are not passed in as strings.
        container_types = ['commands', 'devices']
        for container in container_types:
            if isinstance(getattr(self, container), basestring):
                raise SyntaxError("%r cannot be a string!" % container)

        # Temp hack to avoid ``exceptions.TypeError: Data must not be unicode``
        # Commands that get deserialized from JSON end up as Unicode, and
        # Twisted doesn't like that!
        for idx, cmd in enumerate(self.commands):
            if isinstance(cmd, unicode):
                self.commands[idx] = str(cmd)

        self.deferred = defer.Deferred()

    def from_base(self, results, device, commands=None):
        """Call store_results directly"""
        log.msg('Received %r from %s' % (results, device))
        self.store_results(device, results)

    def from_juniper(self, results, device, commands=None):
        """(Maybe) convert Juniper XML results into a strings"""
        # If we've set force_cli, use to_base() instead
        if self.force_cli:
            return self.from_base(results, device, commands)

        from xml.etree.cElementTree import tostring
        log.msg('Got XML from %s' % device)
        results = [tostring(r) for r in results]
        self.store_results(device, results)

    def store_error(self, device, error):
        """
        Called when an errback is fired.

        Should do somethign meaningful with the errors, but for now just stores
        it as it would a result.
        """
        devname = str(device)
        log.msg("Storing error for %s: %s" % (devname, error))

        if isinstance(error, failure.Failure):
            error = error.value
        devobj = self.device_object(devname, error=repr(error))

        log.msg("Final device object: %r" % devobj)
        self.errors.append(devobj)

        return True

    def device_object(self, device_name, **kwargs):
        """
        Create a basic device dictionary with optional data.
        """
        devobj = dict(device=device_name, **kwargs)
        log.msg("Got device object: %r" % devobj)
        return devobj

    def store_results(self, device, results):
        """
        Called by the parse (from) methods to store command output.

        :device:
            A `~trigger.netdevices.NetDevice` object

        :param results:
            The results to store. Anything you want really.
        """
        devname = str(device)
        log.msg("Storing results for %r: %r" % (devname, results))

        # Basic device object
        devobj = self.device_object(devname, commands=[])

        # Command output will be stored in devobj['commands']
        devobj['commands'] = self.map_results(self.commands, results)

        log.msg("Final device object: %r" % devobj)
        self.results.append(devobj)

        return True

    def map_results(self, commands=None, results=None):
        """
        Return a list of command objects.

        [{'command': 'foo', 'result': 'bar'}, ...]
        """
        log.msg('Mapping results')
        if commands is None:
            commands = self.commands
        if results is None:
            results = []

        cmd_list = []
        for cmd, res in itertools.izip_longest(commands, results):
            if type(Element('')) == type(cmd):
                # XML must die a very horrible death
                cmd = ET.tostring(cmd)
            cmdobj = dict(command=cmd, result=res)
            log.msg("Got command object: %r" % cmdobj)
            cmd_list.append(cmdobj)
        return cmd_list

    def _start(self):
        log.msg("._start() called")
        #self.all_done = False
        #from twisted.internet import reactor
        #reactor.run()

    def _stop(self):
        log.msg("._stop() called")
        log.msg("MY RESULTS ARE: %r" % self.results)
        log.msg("MY  ERRORS ARE: %r" % self.errors)
        self.all_done = True
        #from twisted.internet import reactor
        #reactor.stop()

    def run(self):
        log.msg(".run() called")
        self._add_worker()
        self._start()

        d = self.deferred
        from twisted.internet import reactor
        d.addCallback(self.monitor_result, reactor)
        reactor.callWhenRunning(d.callback, reactor)
        return d

    def monitor_result(self, result, reactor):
        """
        Loop periodically or until the factory stops to monitor the results
        and return them.
        """
        log.msg('>>>>> monitor_result() called')
        log.msg('>>>>> self.all_done = %s' % self.all_done)
        if self.all_done:
            log.msg('>>>>> SENDING RESULTS: %r' % self.results)
            log.msg('>>>>> SENDING  ERRORS: %r' % self.errors)
            #return self.results
            return dict(result=self.results, errors=self.errors)
        return task.deferLater(reactor, 0.5, self.monitor_result, result, reactor)
