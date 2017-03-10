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
