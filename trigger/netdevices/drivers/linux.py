

from trigger.netdevices.drivers.base import registry
from trigger.netdevices.drivers.core import TriggerDriver


class LinuxDriver(TriggerDriver):
    name = 'linux'

    startup_commands = []
    commit_commands = []

    supported_types = ['ROUTER']
    default_type = 'ROUTER'

    startup_commands = []

    prompt_pattern = r'(?:.*(?:\$|#)\s?$)'
    enable_pattern = r'(?:.*(?:\$|#)\s?$)'

    @staticmethod
    def has_error(s):
        """Test whether a string seems to contain an IOS-like error."""
        return False

registry.register(LinuxDriver)
