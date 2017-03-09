

from trigger.netdevices.drivers.ioslike import IOSlikeDriver
from trigger.netdevices.drivers.base import registry


class AristaEOSDriver(IOSlikeDriver):
    name = 'arista'

    supported_types = ['SWITCH']
    default_type = 'SWITCH'

    startup_commands = ['terminal length 0', 'terminal width 999']
registry.register(AristaEOSDriver)
