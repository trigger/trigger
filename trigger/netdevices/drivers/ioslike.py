"""
Base drivers for IOS-like device platforms.
"""

from trigger.netdevices.drivers.core import TriggerDriver


class IOSlikeDriver(TriggerDriver):
    name = 'ioslike'

    startup_commands = ['terminal length 0']
    commit_commands = ['write memory']

    supported_types = ['ROUTER', 'SWITCH', 'FIREWALL']
    default_type = 'ROUTER'

    prompt_pattern = r'\S+(\(config(-[a-z:1-9]+)?\))?[\r\s]*#[\s\b]*$'
    enable_pattern = r'\S+(\(config(-[a-z:1-9]+)?\))?[\r\s]*>[\s\b]*$'

    @staticmethod
    def has_error(s):
        """Test whether a string seems to contain an IOS-like error."""
        tests = (
            s.startswith('%'),                  # Cisco, Arista
            '\n%' in s,                         # A10, Aruba, Foundry
            'syntax error: ' in s.lower(),      # Brocade VDX, F5 BIGIP
            s.startswith('Invalid input -> '),  # Brocade MLX
            s.endswith('Syntax Error'),         # MRV
        )
        return any(tests)
