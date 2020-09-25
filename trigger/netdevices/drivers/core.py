"""

"""

import re

from twisted.internet import defer, reactor

from trigger.conf import settings
from trigger import tacacsrc
from trigger.netdevices.drivers.base import BaseDriver
from trigger.twister3 import ClientTransport, connect


class TriggerDriver(BaseDriver):
    name = 'trigger_driver'
    transport_class = ClientTransport

    def post_init(self):
        # TODO(jathan): Should the TriggerEndpointDispatcher just pass along the
        # creds directly to the TriggerDriver so we don't have to unroll/re-roll
        # them like this?
        self.creds = tacacsrc.Credentials(self.username, self.password, 'foo')
        self.prompt = re.compile(self.prompt_pattern)
        self._endpoint = None

    def generate_endpoint(self, options=None, verifyHostKey=None):
        """
        Generating an endpoint for `~trigger.netdevices.NetDevice`.

        The purpose of this function is to generate endpoint clients for use by
        a `~trigger.netdevices.NetDevice` object.

        :param options: askldfjdkl
        :param verifyHostKey: lskdjfaskld
        """
        if options is None:
            options = {'reconnect': False}

        proto = connect(
            hostname=self.hostname,
            port=self.port,
            creds=self.creds,
            prompt=self.prompt,
            has_error=self.has_error,
            delimiter=self.delimiter,
            startup_commands=self.startup_commands,
            transport_class=self.transport_class,
            options=options,
            verifyHostKey=verifyHostKey,
        )
        return proto.wait()

    @defer.inlineCallbacks
    def perform_open(self, *args, **kwargs):
        """
        Open new session with `~trigger.netdevices.NetDevice`.
        """
        self._endpoint = self.generate_endpoint()

        if self._endpoint is None:
            raise ValueError("Endpoint has not been instantiated.")

        rv = yield self._endpoint
        defer.returnValue(rv)

    @defer.inlineCallbacks
    def perform_close(self):
        """Close an open `~trigger.netdevices.NetDevice` object."""
        if self._endpoint is None:
            raise ValueError("Endpoint has not been instantiated.")

        rv = yield self._endpoint.close()
        defer.returnValue(rv)

    def run_commands(self, commands, on_error=None):
        """
        Public method for scheduling commands onto device.

        Default implementation that schedules commands onto a Device loop.

        This implementation ensures commands are executed sequentially.

        :param commands: List containing commands to schedule onto device loop.
        :type commands: list
        :param on_error: Error handler
        :type  on_error: func

        :Example:
        >>> ...
        >>> dev.open()
        >>> dev.run_commands(['show ip int brief', 'show version'], on_error=lambda x: handle(x))
        """
        if on_error is None:
            on_error = lambda x: x

        d = defer.Deferred()

        result = self._endpoint.add_commands(commands, on_error)
        result.addBoth(on_error)

        return result

    def execute(self, commands):
        self.open()
        result = self.run_commands(commands)

        return result
