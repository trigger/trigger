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
registry.register(JuniperJunosDriver)
