"""

"""

import re

from twisted.internet import defer


from trigger.conf import settings
from trigger.netdevices.drivers.base import BaseDriver


class TriggerDriver(BaseDriver):
    name = 'trigger_driver'

    def post_init(self):
        # self.nodeName is currently hard-coded in trigger.twister2
        # self.nodeName = self.device.nodeName
        self.nodeName = self.hostname

        self.prompt = re.compile(self.prompt_pattern)

        # Set initial endpoint state.
        self.factories = {}
        self._endpoint = None

    def _get_endpoint(self, *args):
        """
        Private method used for generating an endpoint for
        `~trigger.netdevices.NetDevice`.
        """
        from trigger.twister2 import generate_endpoint, TriggerEndpointClientFactory, IoslikeSendExpect
        endpoint = generate_endpoint(self.device).wait()  # FIXME: self.device

        factory = TriggerEndpointClientFactory()
        factory.protocol = IoslikeSendExpect

        self.factories["base"] = factory

        # FIXME(jathan): prompt_pattern could move back to protocol?
        proto = endpoint.connect(factory, prompt_pattern=self.prompt)
        self._proto = proto  # Track this for later, too.

        return proto

    def perform_open(self):
        """
        Open new session with `~trigger.netdevices.NetDevice`.
        """
        def inject_net_device_into_protocol(proto):
            """Now we're only injecting connection for use later."""
            self._conn = proto.transport.conn
            return proto

        self._endpoint = self._get_endpoint()

        if self._endpoint is None:
            raise ValueError("Endpoint has not been instantiated.")

        self.d = self._endpoint.addCallback(
            inject_net_device_into_protocol
        )

    def perform_close(self):
        """Close an open `~trigger.netdevices.NetDevice` object."""
        def disconnect(proto):
            proto.transport.loseConnection()
            return proto

        if self._endpoint is None:
            raise ValueError("Endpoint has not been instantiated.")

        self._endpoint.addCallback(
            disconnect
        )

    def run_channeled_commands(self, commands, on_error=None):
        """
        Public method for scheduling commands onto device.

        This variant allows for efficient multiplexing of commands across multiple vty
        lines where supported ie Arista and Cumulus.

        :param commands: List containing commands to schedule onto device loop.
        :type commands: list
        :param on_error: Error handler
        :type  on_error: func

        :Example:
        >>> ...
        >>> dev.open()
        >>> dev.run_channeled_commands(['show ip int brief', 'show version'], on_error=lambda x: handle(x))
        """
        from trigger.twister2 import TriggerSSHShellClientEndpointBase, IoslikeSendExpect, TriggerEndpointClientFactory

        if on_error is None:
            on_error = lambda x: x

        factory = TriggerEndpointClientFactory()
        factory.protocol = IoslikeSendExpect
        self.factories["channeled"] = factory

        # Here's where we're using self._connect injected on .open()
        ep = TriggerSSHShellClientEndpointBase.existingConnection(self._conn)
        proto = ep.connect(factory, prompt_pattern=self.prompt)

        d = defer.Deferred()

        def inject_commands_into_protocol(proto):
            result = proto.add_commands(commands, on_error)
            result.addCallback(lambda results: d.callback(results))
            result.addBoth(on_error)
            return proto

        proto = proto.addCallbacks(
            inject_commands_into_protocol
        )

        return d

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
        from trigger.twister2 import TriggerSSHShellClientEndpointBase, IoslikeSendExpect, TriggerEndpointClientFactory

        if on_error is None:
            on_error = lambda x: x

        factory = TriggerEndpointClientFactory()
        factory.protocol = IoslikeSendExpect

        proto = self._proto

        d = defer.Deferred()

        def inject_commands_into_protocol(proto):
            result = proto.add_commands(commands, on_error)
            result.addCallback(lambda results: d.callback(results))
            result.addBoth(on_error)
            return proto

        proto = proto.addCallbacks(
            inject_commands_into_protocol
        )

        return d

    def execute(self, commands):
       self.open()
       result = self.run_commands(commands)

       return result
