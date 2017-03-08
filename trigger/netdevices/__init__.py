# -*- coding: utf-8 -*-

"""
The heart and soul of Trigger, NetDevices is an abstract interface to network
device metadata and ACL associations.

Parses :setting:`NETDEVICES_SOURCE` and makes available a dictionary of
`~trigger.netdevices.NetDevice` objects, which is keyed by the FQDN of every
network device.

Other interfaces are non-public.

Example::

    >>> from trigger.netdevices import NetDevices
    >>> nd = NetDevices()
    >>> dev = nd['test1-abc.net.aol.com']
    >>> dev.vendor, dev.make
    (<Vendor: Juniper>, 'MX960-BASE-AC')
    >>> dev.bounce.next_ok('green')
    datetime.datetime(2010, 4, 9, 9, 0, tzinfo=<UTC>)

"""

# Imports
import copy
import itertools
import os
import re
import sys
import time
from UserDict import DictMixin
import xml.etree.cElementTree as ET

from twisted.python import log
from twisted.internet.protocol import Factory
from twisted.internet import reactor
from twisted.internet import defer

from trigger.conf import settings
from trigger.utils import network, parse_node_port
from trigger.utils.url import parse_url
from trigger import changemgmt, exceptions, rancid

from crochet import setup, run_in_reactor, wait_for

from . import loader

try:
    from trigger.acl.db import AclsDB
except ImportError:
    log.msg("ACLs database could not be loaded; Loading without ACL support")
    settings.WITH_ACLS = False


# Constants
JUNIPER_COMMIT = ET.Element('commit-configuration')
JUNIPER_COMMIT_FULL = copy.copy(JUNIPER_COMMIT)
ET.SubElement(JUNIPER_COMMIT_FULL, 'full')


# Exports
__all__ = ['device_match', 'NetDevice', 'NetDevices', 'Vendor']


# Functions
def _munge_source_data(data_source=settings.NETDEVICES_SOURCE):
    """
    Read the source data in the specified format, parse it, and return a

    :param data_source:
        Absolute path to source data file
    """
    log.msg('LOADING FROM: ', data_source)
    kwargs = parse_url(data_source)
    path = kwargs.pop('path')
    return loader.load_metadata(path, **kwargs)


def _populate(netdevices, data_source, production_only, with_acls):
    """
    Populates the NetDevices with NetDevice objects.

    Abstracted from within NetDevices to prevent accidental repopulation of NetDevice
    objects.
    """
    #start = time.time()
    loader, device_data = _munge_source_data(data_source=data_source)
    netdevices.set_loader(loader)

    # Populate AclsDB if `with_acls` is set
    if with_acls:
        log.msg("NetDevices ACL associations: ENABLED")
        aclsdb = AclsDB()
    else:
        log.msg("NetDevices ACL associations: DISABLED")
        aclsdb = None

    # Populate `netdevices` dictionary with `NetDevice` objects!
    for obj in device_data:
        # Don't process it if it's already a NetDevice
        if isinstance(obj, NetDevice):
            dev = obj
        else:
            dev = NetDevice(data=obj, with_acls=aclsdb)

        # Only return devices with adminStatus of 'PRODUCTION' unless
        # `production_only` is True
        if dev.adminStatus.upper() != 'PRODUCTION' and production_only:
            log.msg(
                '[%s] Skipping: adminStatus not PRODUCTION' % dev.nodeName
            )
            continue

        # These checks should be done on generation of netdevices.xml.
        # Skip empty nodenames
        if dev.nodeName is None:
            continue

        # Add to dict
        netdevices.add_device(dev)

    #end = time.time()
    #print 'Took %f seconds' % (end - start)


def device_match(name, production_only=True):
    """
    Return a matching :class:`~trigger.netdevices.NetDevice` object based on
    partial name. Return `None` if no match or if multiple matches is
    cancelled::

        >>> device_match('test')
        2 possible matches found for 'test':
          [ 1] test1-abc.net.aol.com
          [ 2] test2-abc.net.aol.com
          [ 0] Exit

        Enter a device number: 2
        <NetDevice: test2-abc.net.aol.com>

    If there is only a single match, that device object is returned without
    a prompt::

        >>> device_match('fw')
        Matched 'fw1-xyz.net.aol.com'.
        <NetDevice: fw1-xyz.net.aol.com>
    """
    match = None
    nd = NetDevices(production_only)
    try:
        match = nd.find(name)
    except KeyError:
        matches = nd.search(name)
        if matches:
            if len(matches) == 1:
                single = matches[0]
                print "Matched '%s'." % single
                return single

            print "%d possible matches found for '%s':" % (len(matches), name)

            matches.sort()
            for num, shortname in enumerate(matches):
                print ' [%s] %s' % (str(num+1).rjust(2), shortname)
            print ' [ 0] Exit\n'

            choice = input('Enter a device number: ') - 1
            match = None if choice < 0 else matches[choice]
            log.msg('Choice: %s' % choice)
            log.msg('You chose: %s' % match)
        else:
            print "No matches for '%s'." % name

    return match


# Classes
class NetDevice(object):
    """
    An object that represents a distinct network device and its metadata.

    Almost all of the attributes are populated by
    `~trigger.netdevices._populate()` and are mostly dependent upon the source
    data. This is prone to implementation problems and should be revisited in
    the long-run as there are certain fields that are baked into the core
    functionality of Trigger.

    Users usually won't create these objects directly! Rely instead upon
    `~trigger.netdevice.NetDevices` to do this for you.
    """

    def __init__(self, data=None, with_acls=None):
        # Here comes all of the bare minimum set of attributes a NetDevice
        # object needs for basic functionality within the existing suite.

        # Hostname
        self.nodeName = None
        self.nodePort = None

        # Hardware Info
        self.deviceType = None
        self.make = None
        self.manufacturer = settings.FALLBACK_MANUFACTURER
        self.vendor = None
        self.model = None
        self.serialNumber = None

        # Administrivia
        self.adminStatus = settings.DEFAULT_ADMIN_STATUS
        self.assetID = None
        self.budgetCode = None
        self.budgetName = None
        self.enablePW = None
        self.owningTeam = None
        self.owner = None
        self.onCallName = None
        self.operationStatus = None
        self.lastUpdate = None
        self.lifecycleStatus = None
        self.projectName = None

        # Location
        self.site = None
        self.room = None
        self.coordinate = None

        # If `data` has been passed, use it to update our attributes
        if data is not None:
            self._populate_data(data)

        # Set node remote port based on "hostname:port" as nodeName
        self._set_node_port()

        # Cleanup the attributes (strip whitespace, lowercase values, etc.)
        self._cleanup_attributes()

        # Map the manufacturer name to a Vendor object that has extra sauce
        if self.manufacturer is not None:
            self.vendor = vendor_factory(self.manufacturer)

        # Use the vendor to populate the deviceType if it's not set already
        if self.deviceType is None:
            self._populate_deviceType()

        # ACLs (defaults to empty sets)
        self.explicit_acls = self.implicit_acls = self.acls = self.bulk_acls = set()
        if with_acls:
            log.msg('[%s] Populating ACLs' % self.nodeName)
            self._populate_acls(aclsdb=with_acls)

        # Bind the correct execute/connect methods based on deviceType
        self._bind_dynamic_methods()

        # Set the correct command(s) to run on startup based on deviceType
        self.startup_commands = self._set_startup_commands()

        # Assign the configuration commit commands (e.g. 'write memory')
        self.commit_commands = self._set_commit_commands()

        # Determine whether we require an async pty SSH channel
        self.requires_async_pty = self._set_requires_async_pty()

        # Set the correct line-ending per vendor
        self.delimiter = self._set_delimiter()

        # Set initial endpoint state
        self.factories = {}
        self._connected = False
        self._endpoint = None

    def _populate_data(self, data):
        """
        Populate the custom attribute data

        :param data:
            An iterable of key/value pairs
        """
        self.__dict__.update(data) # Better hope this is a dict!

    def _cleanup_attributes(self):
        """Perform various cleanup actions. Abstracted for customization."""
        # Lowercase the nodeName for completeness.
        if self.nodeName is not None:
            self.nodeName = self.nodeName.lower()

        if self.deviceType is not None:
            self.deviceType = self.deviceType.upper()

        # Make sure the password is bytes not unicode
        if self.enablePW is not None:
            self.enablePW = str(self.enablePW)

        # Cleanup whitespace from owning team
        if self.owningTeam is not None:
            self.owningTeam = self.owningTeam.strip()

        # Map deviceStatus to adminStatus when data source is RANCID
        if hasattr(self, 'deviceStatus'):
            STATUS_MAP = {
                'up': 'PRODUCTION',
                'down': 'NON-PRODUCTION',
            }
            self.adminStatus = STATUS_MAP.get(self.deviceStatus, STATUS_MAP['up'])

    def _set_node_port(self):
        """Set the freakin' TCP port"""
        # If nodename is set, try to parse out a nodePort
        if self.nodeName is not None:
            nodeport_info = parse_node_port(self.nodeName)
            nodeName, nodePort = nodeport_info

            # If the nodeName differs, use it to replace the one we parsed
            if nodeName != self.nodeName:
                self.nodeName = nodeName

            # If the port isn't set, set it
            if nodePort is not None:
                self.nodePort = nodePort
                return None

        # Make sure the port is an integer if it's not None
        if self.nodePort is not None and isinstance(self.nodePort, basestring):
            self.nodePort = int(self.nodePort)

    def _populate_deviceType(self):
        """Try to make a guess what the device type is"""
        self.deviceType = settings.DEFAULT_TYPES.get(self.vendor.name,
                                                     settings.FALLBACK_TYPE)

    def _set_requires_async_pty(self):
        """
        Set whether a device requires an async pty (see:
        `~trigger.twister.TriggerSSHAsyncPtyChannel`).
        """
        RULES = (
            self.vendor in (
                'a10', 'arista', 'aruba', 'cisco', 'cumulus', 'force10'
            ),
            self.is_brocade_vdx(),
        )
        return any(RULES)

    def _set_delimiter(self):
        """
        Set the delimiter to use for line-endings.
        """
        default = '\n'
        delimiter_map = {
            'force10': '\r\n',
        }
        delimiter = delimiter_map.get(self.vendor.name, default)
        return delimiter

    def _set_startup_commands(self):
        """
        Set the commands to run at startup. For now they are just ones to
        disable pagination.
        """
        def get_vendor_name():
            """Return the vendor name for startup commands lookup."""
            if self.is_brocade_vdx():
                return 'brocade_vdx'
            elif self.is_cisco_asa():
                return 'cisco_asa'
            elif self.is_netscreen():
                return 'netscreen'
            else:
                return self.vendor.name

        paging_map = settings.STARTUP_COMMANDS_MAP
        cmds = paging_map.get(get_vendor_name())

        if cmds is not None:
            return cmds

        return []

    def _set_commit_commands(self):
        """
        Return the proper "commit" command. (e.g. write mem, etc.)
        """
        if self.is_ioslike():
            return self._ioslike_commit()
        elif self.is_netscaler() or self.is_netscreen():
            return ['save config']
        elif self.vendor == 'juniper':
            return self._juniper_commit()
        elif self.vendor == 'paloalto':
            return ['commit']
        elif self.vendor == 'pica8':
            return ['commit']
        elif self.vendor == 'mrv':
            return ['save configuration flash']
        elif self.vendor == 'f5':
            return ['save sys config']
        else:
            return []

    def _ioslike_commit(self):
        """
        Return proper 'write memory' command for IOS-like devices.
        """
        if self.is_brocade_vdx() or self.vendor == 'dell':
            return ['copy running-config startup-config', 'y']
        elif self.is_cisco_nexus():
            return ['copy running-config startup-config']
        else:
            return ['write memory']

    def _juniper_commit(self, fields=settings.JUNIPER_FULL_COMMIT_FIELDS):
        """
        Return proper ``commit-configuration`` element for a Juniper
        device.
        """
        default = [JUNIPER_COMMIT]
        if not fields:
            return default

        # Either it's a normal "commit-configuration"
        for attr, val in fields.iteritems():
            if not getattr(self, attr) == val:
                return default

        # Or it's a "commit-configuration full"
        return [JUNIPER_COMMIT_FULL]

    def _bind_dynamic_methods(self):
        """
        Bind dynamic methods to the instance. Currently does these:

            + Dynamically bind ~trigger.twister.excute` to .execute()
            + Dynamically bind ~trigger.twister.connect` to .connect()

        Note that these both rely on the value of the ``vendor`` attribute.
        """
        from trigger import twister
        self.execute = twister.execute.__get__(self, self.__class__)
        self.connect = twister.connect.__get__(self, self.__class__)

    def _populate_acls(self, aclsdb=None):
        """
        Populate the associated ACLs for this device.

        :param aclsdb:
            An `~trigger.acl.db.AclsDB` object.
        """
        if not aclsdb:
            return None

        acls_dict = aclsdb.get_acl_dict(self)
        self.explicit_acls = acls_dict['explicit']
        self.implicit_acls = acls_dict['implicit']
        self.acls = acls_dict['all']

    def __str__(self):
        return self.nodeName

    def __repr__(self):
        return "<NetDevice: %s>" % self.nodeName

    def __cmp__(self, other):
        if self.nodeName > other.nodeName:
            return 1
        elif self.nodeName < other.nodeName:
            return -1
        else:
            return 0

    @property
    def bounce(self):
        return changemgmt.bounce(self)

    @property
    def shortName(self):
        return self.nodeName.split('.', 1)[0]

    @property
    def os(self):
        vendor_mapping = settings.TEXTFSM_VENDOR_MAPPINGS
        try:
            oss = vendor_mapping[self.vendor]
            if self.operatingSystem.lower() in oss:
                return "{0}_{1}".format(self.vendor, self.operatingSystem.lower())
        except:
            log.msg("""Unable to find template for given device.
                    Check to see if your netdevices object has the 'platform' key.
                    Otherwise template does not exist.""")
            return None

    def _get_endpoint(self, *args):
        """Private method used for generating an endpoint for `~trigger.netdevices.NetDevice`."""
        from trigger.twister2 import generate_endpoint, TriggerEndpointClientFactory, IoslikeSendExpect
        endpoint = generate_endpoint(self).wait()

        factory = TriggerEndpointClientFactory()
        factory.protocol = IoslikeSendExpect

        self.factories["base"] = factory

        # FIXME(jathan): prompt_pattern could move back to protocol?
        prompt = re.compile(settings.IOSLIKE_PROMPT_PAT)
        proto = endpoint.connect(factory, prompt_pattern=prompt)
        self._proto = proto  # Track this for later, too.

        return proto

    def open(self):
        """Open new session with `~trigger.netdevices.NetDevice`.
        
        Example:
            >>> nd = NetDevices()
            >>> dev = nd.find('arista-sw1.demo.local')
            >>> dev.open()

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

        self._connected = True
        return self._connected

    def close(self):
        """Close an open `~trigger.netdevices.NetDevice` object."""
        def disconnect(proto):
            proto.transport.loseConnection()
            return proto

        if self._endpoint is None:
            raise ValueError("Endpoint has not been instantiated.")

        self._endpoint.addCallback(
            disconnect
        )

        self._connected = False
        return

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def get_results(self):
        self._results = []
        while len(self._results) != len(self.commands):
            pass
        return self._results

    def run_channeled_commands(self, commands, on_error=None):
        """Public method for scheduling commands onto device.

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
        prompt = re.compile(settings.IOSLIKE_PROMPT_PAT)
        proto = ep.connect(factory, prompt_pattern=prompt)

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
        """Public method for scheduling commands onto device.

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

    @property
    def connected(self):
        return self._connected

    def allowable(self, action, when=None):
        """
        Return whether it's okay to perform the specified ``action``.

        False means a bounce window conflict. For now ``'load-acl'`` is the
        only valid action and moratorium status is not checked.

        :param action:
            The action to check.

        :param when:
            A datetime object.
        """
        assert action == 'load-acl'
        return self.bounce.status(when) == changemgmt.BounceStatus('green')

    def next_ok(self, action, when=None):
        """
        Return the next time at or after the specified time (default now)
        that it will be ok to perform the specified action.

        :param action:
            The action to check.

        :param when:
            A datetime object.
        """
        assert action == 'load-acl'
        return self.bounce.next_ok(changemgmt.BounceStatus('green'), when)

    def is_router(self):
        """Am I a router?"""
        return self.deviceType == 'ROUTER'

    def is_switch(self):
        """Am I a switch?"""
        return self.deviceType == 'SWITCH'

    def is_firewall(self):
        """Am I a firewall?"""
        return self.deviceType == 'FIREWALL'

    def is_netscaler(self):
        """Am I a NetScaler?"""
        return all([self.is_switch(), self.vendor=='citrix'])

    def is_pica8(self):
        """Am I a Pica8?"""
        ## This is only really needed because pica8 
        ## doesn't have a global command to disable paging
        ## so we need to do some special magic.
        return all([self.vendor=='pica8'])

    def is_netscreen(self):
        """Am I a NetScreen running ScreenOS?"""
        # Are we even a firewall?
        if not self.is_firewall():
            return False

        # If vendor or make is netscreen, automatically True
        make_netscreen = self.make is not None and self.make.lower() == 'netscreen'
        if self.vendor == 'netscreen' or make_netscreen:
            return True

        # Final check: Are we made by Juniper and an SSG? This requires that
        # make or model is populated and has the word 'ssg' in it. This still
        # fails if it's an SSG running JunOS, but this is not an edge case we
        # can easily support at this time.
        is_ssg = (
            (self.model is not None and 'ssg' in self.model.lower()) or
            (self.make is not None and 'ssg' in self.make.lower())
        )
        return self.vendor == 'juniper' and is_ssg

    def is_ioslike(self):
        """
        Am I an IOS-like device (as determined by :setting:`IOSLIKE_VENDORS`)?
        """
        return self.vendor in settings.IOSLIKE_VENDORS

    def is_cumulus(self):
        """
        Am I running Cumulus?
        """
        return self.vendor == 'cumulus'

    def is_brocade_vdx(self):
        """
        Am I a Brocade VDX switch?

        This is used to account for the disparity between the Brocade FCX
        switches (which behave like Foundry devices) and the Brocade VDX
        switches (which behave differently from classic Foundry devices).
        """
        if hasattr(self, '_is_brocade_vdx'):
            return self._is_brocade_vdx

        if not (self.vendor == 'brocade' and self.is_switch()):
            self._is_brocade_vdx = False
            return False

        if self.make is not None:
            self._is_brocade_vdx = 'vdx' in self.make.lower()
        return self._is_brocade_vdx

    def is_cisco_asa(self):
        """
        Am I a Cisco ASA Firewall?

        This is used to account for slight differences in the commands that
        may be used between Cisco's ASA and IOS platforms. Cisco ASA is still
        very IOS-like, but there are still several gotcha's between the
        platforms.

        Will return True if vendor is Cisco and platform is Firewall. This
        is to allow operability if using .csv NetDevices and pretty safe to
        assume considering ASA (was PIX) are Cisco's flagship(if not only)
        Firewalls.
        """
        if hasattr(self, '_is_cisco_asa'):
            return self._is_cisco_asa

        if not (self.vendor == 'cisco' and self.is_firewall()):
            self._is_cisco_asa = False
            return False

        if self.make is not None:
            self._is_cisco_asa = 'asa' in self.make.lower()

        self._is_cisco_asa = self.vendor == 'cisco' and self.is_firewall()

        return self._is_cisco_asa

    def is_cisco_nexus(self):
        """
        Am I a Cisco Nexus device?
        """
        words = (self.make, self.model)
        patterns = ('n.k', 'nexus')  # Patterns to match
        pairs = itertools.product(patterns, words)

        for pat, word in pairs:
            if word and re.search(pat, word.lower()):
                return True
        return False

    def _ssh_enabled(self, disabled_mapping):
        """Check whether vendor/type is enabled against the given mapping."""
        disabled_types = disabled_mapping.get(self.vendor.name, [])
        return self.deviceType not in disabled_types

    def has_ssh(self):
        """Am I even listening on SSH?"""
        return network.test_ssh(self.nodeName)

    def _can_ssh(self, method):
        """
        Am I enabled to use SSH for the given method in Trigger settings, and
        if so do I even have SSH?

        :param method: One of ('pty', 'async')
        """
        METHOD_MAP = {
            'pty': settings.SSH_PTY_DISABLED,
            'async': settings.SSH_ASYNC_DISABLED,
        }
        assert method in METHOD_MAP
        method_enabled = self._ssh_enabled(METHOD_MAP[method])

        return method_enabled and self.has_ssh()

    def can_ssh_async(self):
        """Am I enabled to use SSH async?"""
        return self._can_ssh('async')

    def can_ssh_pty(self):
        """Am I enabled to use SSH pty?"""
        return self._can_ssh('pty')

    def is_reachable(self):
        """Do I respond to a ping?"""
        return network.ping(self.nodeName)

    def dump(self):
        """Prints details for a device."""
        dev = self
        print
        print '\tHostname:         ', dev.nodeName
        print '\tOwning Org.:      ', dev.owner
        print '\tOwning Team:      ', dev.owningTeam
        print '\tOnCall Team:      ', dev.onCallName
        print
        print '\tVendor:           ', '%s (%s)' % (dev.vendor.title, dev.manufacturer)
        #print '\tManufacturer:     ', dev.manufacturer
        print '\tMake:             ', dev.make
        print '\tModel:            ', dev.model
        print '\tType:             ', dev.deviceType
        print '\tLocation:         ', dev.site, dev.room, dev.coordinate
        print
        print '\tProject:          ', dev.projectName
        print '\tSerial:           ', dev.serialNumber
        print '\tAsset Tag:        ', dev.assetID
        print '\tBudget Code:      ', '%s (%s)' % (dev.budgetCode, dev.budgetName)
        print
        print '\tAdmin Status:     ', dev.adminStatus
        print '\tLifecycle Status: ', dev.lifecycleStatus
        print '\tOperation Status: ', dev.operationStatus
        print '\tLast Updated:     ', dev.lastUpdate
        print

class Vendor(object):
    """
    Map a manufacturer name to Trigger's canonical name.

    Given a manufacturer name like 'CISCO SYSTEMS', this will attempt to map it
    to the canonical vendor name specified in ``settings.VENDOR_MAP``. If this
    can't be done, attempt to split the name up ('CISCO, 'SYSTEMS') and see if
    any of the words map. An exception is raised as a last resort.

    This exposes a normalized name that can be used in the event of a
    multi-word canonical name.
    """
    def __init__(self, manufacturer=None):
        """
        :param manufacturer:
            The literal or "internal" name for a vendor that is to be mapped to
            its canonical name.
        """
        if manufacturer is None:
            raise SyntaxError('You must specify a `manufacturer` name')

        self.manufacturer = manufacturer
        self.name = self.determine_vendor(manufacturer)
        self.title = self.name.title()
        self.prompt_pattern = self._get_prompt_pattern(self.name)

    def determine_vendor(self, manufacturer):
        """Try to turn the provided vendor name into the cname."""
        vendor = settings.VENDOR_MAP.get(manufacturer)
        if vendor is None:
            mparts = [w for w in manufacturer.lower().split()]
            for word in mparts:
                if word in settings.SUPPORTED_VENDORS:
                    vendor = word
                    break
                else:
                    # Safe fallback to first word
                    vendor = mparts[0]

        return vendor

    def _get_prompt_pattern(self, vendor, prompt_patterns=None):
        """
        Map the vendor name to the appropriate ``prompt_pattern`` defined in
        :setting:`PROMPT_PATTERNS`.
        """
        if prompt_patterns is None:
            prompt_patterns = settings.PROMPT_PATTERNS

        # Try to get it by vendor
        pat = prompt_patterns.get(vendor)
        if pat is not None:
            return pat

        # Try to map it by IOS-like vendors...
        if vendor in settings.IOSLIKE_VENDORS:
            return settings.IOSLIKE_PROMPT_PAT

        # Or fall back to the default
        return settings.DEFAULT_PROMPT_PAT

    @property
    def normalized(self):
        """Return the normalized name for the vendor."""
        return self.name.replace(' ', '_').lower()

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.title)

    def __eq__(self, other):
        return self.name.__eq__(Vendor(str(other)).name)

    def __contains__(self, other):
        return self.name.__contains__(Vendor(str(other)).name)

    def __hash__(self):
        return hash(self.name)

    def lower(self):
        return self.normalized

_vendor_registry = {}
def vendor_factory(vendor_name):
    """
    Given a full name of a vendor, retrieve or create the canonical
    `~trigger.netdevices.Vendor` object.

    Vendor instances are cached to improve startup speed.

    :param vendor_name:
        The vendor's full manufacturer name (e.g. 'CISCO SYSTEMS')
    """
    return _vendor_registry.setdefault(vendor_name, Vendor(vendor_name))


class NetDevices(DictMixin):
    """
    Returns an immutable Singleton dictionary of
    `~trigger.netdevices.NetDevice` objects.

    By default it will only return devices for which
    ``adminStatus=='PRODUCTION'``.

    There are hardly any use cases where ``NON-PRODUCTION`` devices are needed,
    and it can cause real bugs of two sorts:

      1. trying to contact unreachable devices and reporting spurious failures,
      2. hot spares with the same ``nodeName``.

    You may override this by passing ``production_only=False``.
    """
    _Singleton = None

    class _actual(object):
        """
        This is the real class that stays active upon instantiation. All
        attributes are inherited by NetDevices from this object. This means you
        do NOT reference ``_actual`` itself, and instead call the methods from
        the parent object.

        Right::

            >>> nd = NetDevices()
            >>> nd.search('fw')
            [<NetDevice: fw1-xyz.net.aol.com>]

        Wrong::

            >>> nd._actual.search('fw')
            Traceback (most recent call last):
              File "<stdin>", line 1, in <module>
            TypeError: unbound method match() must be called with _actual
            instance as first argument (got str instance instead)
        """
        def __init__(self, production_only=True, with_acls=None):
            self.loader = None
            self.__dict = {}

            _populate(netdevices=self,
                      data_source=settings.NETDEVICES_SOURCE,
                      production_only=production_only, with_acls=with_acls)

        def set_loader(self, loader):
            """
            Set the NetDevices loader and initialize internal dictionary.

            :param loader:
                A `~trigger.netdevices.loader.BaseLoader` plugin instance
            """
            self.loader = loader

            if hasattr(loader, '_dict'):
                log.msg('Installing NetDevices._dict from loader plugin!')
            else:
                log.msg('Installing NetDevice._dict internally!')

        @property
        def _dict(self):
            """
            If the loader has an inner _dict, store objects on that instead.
            """
            if hasattr(self.loader, '_dict'):
                return self.loader._dict
            else:
                return self.__dict

        def add_device(self, device):
            """
            Add a device object to the store.

            :param device:
                `~trigger.netdevices.NetDevice` object
            """
            self._dict[device.nodeName] = device

        def __getitem__(self, key):
            return self._dict[key]

        def __contains__(self, item):
            return item in self._dict

        def keys(self):
            return self._dict.keys()

        def values(self):
            return self._dict.values()

        def find(self, key):
            """
            Return either the exact nodename, or a unique dot-delimited
            prefix.  For example, if there is a node 'test1-abc.net.aol.com',
            then any of find('test1-abc') or find('test1-abc.net') or
            find('test1-abc.net.aol.com') will match, but not find('test1').

            This method can be overloaded in NetDevices loader plugins to
            customize the behavior as dictated by the plugin.

            :param string key: Hostname prefix to find.
            :returns: NetDevice object
            """
            key = key.lower()

            # Try to use the loader plugin first.
            if hasattr(self.loader, 'find'):
                return self.loader.find(key)

            # Or if there's a key, return that.
            elif key in self:
                return self[key]

            matches = [x for x in self.keys() if x.startswith(key + '.')]

            if matches:
                return self[matches[0]]
            raise KeyError(key)

        def all(self):
            """
            Returns all NetDevice objects.

            This method can be overloaded in NetDevices loader plugins to
            customize the behavior as dictated by the plugin.
            """
            if hasattr(self.loader, 'all'):
                return self.loader.all()
            return self.values()

        def search(self, token, field='nodeName'):
            """
            Returns a list of NetDevice objects where other is in
            ``dev.nodeName``. The getattr call in the search will allow a
            ``AttributeError`` from a bogus field lookup so that you
            don't get an empty list thinking you performed a legit query.

            For example, this::

                >>> field = 'bacon'
                >>> [x for x in nd.all() if 'ash' in getattr(x, field)]
                Traceback (most recent call last):
                File "<stdin>", line 1, in <module>
                AttributeError: 'NetDevice' object has no attribute 'bacon'

            Is better than this::

                >>> [x for x in nd.all() if 'ash' in getattr(x, field, '')]
                []

            Because then you know that 'bacon' isn't a field you can search on.

            :param string token: Token to search match on in @field
            :param string field: The field to match on when searching
            :returns: List of NetDevice objects
            """
            # We could actually just make this call match() to make this
            # case-insensitive as well. But we won't yet because of possible
            # implications in outside dependencies.
            #return self.match(**{field:token})

            return [x for x in self.all() if token in getattr(x, field)]

        def match(self, **kwargs):
            """
            Attempt to match values to all keys in @kwargs by dynamically
            building a list comprehension. Will throw errors if the keys don't
            match legit NetDevice attributes.

            Keys and values are case IN-senstitive. Matches against non-string
            values will FAIL.

            This method can be overloaded in NetDevices loader plugins to
            customize the behavior as dictated by the plugin. If
            ``skip_loader=True`` the built-in method will be used instead.

            Example by reference::

                >>> nd = NetDevices()
                >>> myargs = {'onCallName':'Data Center', 'model':'FCSLB'}
                >>> mydevices = nd(**myargs)

            Example by keyword arguments::

                >>> mydevices = nd(oncallname='data center', model='fcslb')

            :returns: List of NetDevice objects
            """
            skip_loader = kwargs.pop('skip_loader', False)
            if skip_loader:
                log.msg('Skipping loader.match()')

            if not skip_loader and hasattr(self.loader, 'match'):
                log.msg('Calling loader.match()')
                return self.loader.match(**kwargs)

            all_field_names = getattr(self, '_all_field_names', {})
            devices = self.all()

            # Cache the field names the first time .match() is called.
            if not all_field_names:
                # Merge in field_names from every NetDevice
                for dev in devices:
                    dev_fields = ((f.lower(), f) for f in dev.__dict__)
                    all_field_names.update(dev_fields)
                self._all_field_names = all_field_names

            def map_attr(attr):
                """Helper function for lower-to-regular attribute mapping."""
                return self._all_field_names[attr.lower()]

            # Use list comp. to keep filtering out the devices.
            for attr, val in kwargs.iteritems():
                attr = map_attr(attr)
                val = str(val).lower()
                devices = [
                    d for d in devices if (
                        val in str(getattr(d, attr, '')).lower()
                    )
                ]

            return devices

        def get_devices_by_type(self, devtype):
            """
            Returns a list of NetDevice objects with deviceType matching type.

            Known deviceTypes: ['FIREWALL', 'ROUTER', 'SWITCH']
            """
            return [x for x in self.values() if x.deviceType == devtype]

        def list_switches(self):
            """Returns a list of NetDevice objects with deviceType of SWITCH"""
            return self.get_devices_by_type('SWITCH')

        def list_routers(self):
            """Returns a list of NetDevice objects with deviceType of ROUTER"""
            return self.get_devices_by_type('ROUTER')

        def list_firewalls(self):
            """Returns a list of NetDevice objects with deviceType of FIREWALL"""
            return self.get_devices_by_type('FIREWALL')

    def __init__(self, production_only=True, with_acls=None):
        """
        :param production_only:
            Whether to require devices to have ``adminStatus=='PRODUCTION'``.

        :param with_acls:
            Whether to load ACL associations (requires Redis). Defaults to whatever
            is specified in settings.WITH_ACLS
        """
        if with_acls is None:
            with_acls = settings.WITH_ACLS
        classobj = self.__class__
        if classobj._Singleton is None:
            classobj._Singleton = classobj._actual(production_only=production_only,
                                                   with_acls=with_acls)

    def __getattr__(self, attr):
        return getattr(self.__class__._Singleton, attr)

    def __setattr__(self, attr, value):
        return setattr(self.__class__._Singleton, attr, value)

    def reload(self, **kwargs):
        """Reload NetDevices metadata."""
        log.msg('Reloading NetDevices.')
        classobj = self.__class__
        classobj._Singleton = classobj._actual(**kwargs)
