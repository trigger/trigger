

from trigger.netdevices.drivers.base import registry
from trigger.netdevices.drivers.ioslike import IOSlikeDriver
from trigger.twister3 import ClientTransport
from twisted.conch.ssh import transport


class CiscoClientTransport(ClientTransport):
    """Custom SSH transport for "certain" Cisco devices."""

    def connectionMade(self):
        """
        Once the connection is up, set the ciphers but don't do anything else!
        """
        self.currentEncryptions = transport.SSHCiphers(
            'none', 'none', 'none', 'none'
        )
        self.currentEncryptions.setKeys('', '', '', '', '', '')

    def dataReceived(self, data):
        """
        Explicity override version detection for edge cases where "SSH-"
        isn't on the first line of incoming data.
        """
        preVersion = self.gotVersion

        # This call should populate the SSH version and carry on as usual.
        transport.SSHClientTransport.dataReceived(self, data)

        # We have now seen the SSH version in the banner and signal that the
        # connection has been made successfully.
        if self.gotVersion and not preVersion:
            transport.SSHClientTransport.connectionMade(self)


class CiscoIOSDriver(IOSlikeDriver):
    name = 'cisco'

    transport_class = CiscoClientTransport
registry.register(CiscoIOSDriver)


class CiscoASADriver(IOSlikeDriver):
    name = 'cisco_asa'
    startup_commands = ['terminal pager 0']
registry.register(CiscoASADriver)


class CiscoNexusDriver(IOSlikeDriver):
    name = 'cisco_nexus'
    commit_commands = ['copy running-config startup-config']
registry.register(CiscoNexusDriver)
