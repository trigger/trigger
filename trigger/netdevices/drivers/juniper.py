"""
Base drivers for Juniper device platforms.
"""

from trigger.netdevices.drivers.core import TriggerDriver
from trigger.netdevices.drivers.base import registry


class JuniperJunosDriver(TriggerDriver):
    name = 'juniper'

    startup_commands = ['set cli screen-length 0']
    commit_commands = ['commit and-quit']

    supported_types = ['ROUTER', 'SWITCH', 'FIREWALL']
    default_type = 'ROUTER'

    prompt_pattern = r'(?:\S+\@)?\S+(?:\>|#)\s$'
    enable_pattern = None

    @staticmethod
    def has_error(s):
        """Test whether a string seems to contain an Juniper error."""
        tests = (
            'unknown command.' in s,
            'syntax error, ' in s,
            'invalid value.' in s,
            'missing argument.' in s,
        )
        return any(tests)
registry.register(JuniperJunosDriver)
