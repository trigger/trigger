

from trigger.netdevices.drivers.ioslike import IOSlikeDriver
from trigger.netdevices.drivers.base import registry


class CiscoIOSDriver(IOSlikeDriver):
    # name = 'cisco_ios'
    name = 'cisco'
registry.register(CiscoIOSDriver)


class CiscoASADriver(IOSlikeDriver):
    name = 'cisco_asa'
    startup_commands = ['terminal pager 0']
registry.register(CiscoASADriver)


class CiscoNexusDriver(IOSlikeDriver):
    name = 'cisco_nexus'
    commit_commands = ['copy running-config startup-config']
registry.register(CiscoNexusDriver)
