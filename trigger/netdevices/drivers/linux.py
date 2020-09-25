"""
Simple Linux driver.
"""

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

    @staticmethod
    def has_error(s):
        """Test whether a string seems to contain an error."""
        tests = (
            'command not found' in s.lower(),
            'no such file or directory' in s.lower(),
        )
        return any(tests)
registry.register(LinuxDriver)
