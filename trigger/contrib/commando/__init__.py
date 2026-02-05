"""trigger.contrib.commando.
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

__author__ = "Jathan McCollum, Mike Biancaniello"
__maintainer__ = "Jathan McCollum"
__email__ = "jathan@gmail.com"
__copyright__ = "Copyright 2012-2013, AOL Inc."
__version__ = "0.2.1"


# Imports
import itertools
import os
import pickle
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element

from twisted.internet import defer, task
from twisted.python import failure, log

from trigger import exceptions
from trigger.cmds import Commando

# Exports
__all__ = ("CommandoApplication",)


# Enable Deferred debuging if ``DEBUG`` is set.
if os.getenv("DEBUG"):
    defer.setDebugging(True)


# Classes
class CommandoApplication(Commando):
    """Commando subclass to be used in an application where the reactor is always
    running (e.g. twistd or an application server).

    Stores results as a list of dictionaries ideal for serializing to JSON.
    """

    timeout = 5

    def __init__(self, *args, **kwargs):
        self.all_done = False
        self.results = []
        self.errors = []
        super().__init__(*args, **kwargs)

        if not self.devices:
            msg = "You must specify some `devices` to interact with!"
            raise exceptions.ImproperlyConfigured(
                msg,
            )
        # Commenting out because sometimes the cmds come in the to_<vendor> methods

        # Make sure that the specified containers are not passed in as strings.
        container_types = ["commands", "devices"]
        for container in container_types:
            if isinstance(getattr(self, container), str):
                msg = f"{container!r} cannot be a string!"
                raise SyntaxError(msg)

        # In Python 3, all strings are unicode by default, so no conversion needed
        # Commands that get deserialized from JSON are already strings
        # This block is kept for compatibility but is now a no-op
        for idx, cmd in enumerate(self.commands):
            if isinstance(cmd, str):
                self.commands[idx] = str(cmd)

        self.deferred = defer.Deferred()

    def from_base(self, results, device, commands=None):
        """Call store_results directly."""
        log.msg(f"Received {results!r} from {device}")
        self.store_results(device, results)

    def from_juniper(self, results, device, commands=None):
        """(Maybe) convert Juniper XML results into a strings."""
        # If we've set force_cli, use to_base() instead
        if self.force_cli:
            return self.from_base(results, device, commands)

        from xml.etree.ElementTree import tostring

        log.msg(f"Got XML from {device}")
        results = [tostring(r) for r in results]
        self.store_results(device, results)
        return None

    def store_error(self, device, error):
        """Called when an errback is fired.

        Should do somethign meaningful with the errors, but for now just stores
        it as it would a result.
        """
        devname = str(device)
        log.msg(f"Storing error for {devname}: {error}")

        if isinstance(error, failure.Failure):
            error = error.value
        devobj = self.device_object(devname, error=repr(error))

        log.msg(f"Final device object: {devobj!r}")
        self.errors.append(devobj)

        return True

    def device_object(self, device_name, **kwargs):
        """Create a basic device dictionary with optional data.
        """
        devobj = dict(device=device_name, **kwargs)
        log.msg(f"Got device object: {devobj!r}")
        return devobj

    def store_results(self, device, results):
        """Called by the parse (from) methods to store command output.

        :device:
            A `~trigger.netdevices.NetDevice` object

        :param results:
            The results to store. Anything you want really.
        """
        devname = str(device)
        log.msg(f"Storing results for {devname!r}: {results!r}")

        # Basic device object
        devobj = self.device_object(devname, commands=[])

        # Command output will be stored in devobj['commands']
        devobj["commands"] = self.map_results(self.commands, results)

        log.msg(f"Final device object: {devobj!r}")
        self.results.append(devobj)

        return True

    def map_results(self, commands=None, results=None):
        """Return a list of command objects.

        [{'command': 'foo', 'result': 'bar'}, ...]
        """
        log.msg("Mapping results")
        if commands is None:
            commands = self.commands
        if results is None:
            results = []

        cmd_list = []
        for cmd, res in itertools.zip_longest(commands, results):
            if type(Element("")) == type(cmd):
                # XML must die a very horrible death
                cmd = ET.tostring(cmd)  # noqa: PLW2901
            cmdobj = dict(command=cmd, result=res)
            log.msg(f"Got command object: {cmdobj!r}")
            cmd_list.append(cmdobj)
        return cmd_list

    def _start(self):
        log.msg("._start() called")

    def _stop(self):
        log.msg("._stop() called")
        log.msg(f"MY RESULTS ARE: {self.results!r}")
        log.msg(f"MY  ERRORS ARE: {self.errors!r}")
        self.all_done = True

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
        """Loop periodically or until the factory stops to monitor the results
        and return them.
        """
        log.msg(">>>>> monitor_result() called")
        log.msg(f">>>>> self.all_done = {self.all_done}")
        if self.all_done:
            log.msg(f">>>>> SENDING RESULTS: {self.results!r}")
            log.msg(f">>>>> SENDING  ERRORS: {self.errors!r}")
            return dict(result=self.results, errors=self.errors)
        return task.deferLater(reactor, 0.5, self.monitor_result, result, reactor)
