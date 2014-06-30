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

__author__ = 'Jathan McCollum, Eileen Tschetter, Mark Thomas, Michael Shields'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2006-2013, AOL Inc.; 2013 Salesforce.com'
__version__ = '2.3'

# Imports
import copy
import itertools
import os
import sys
import time
from twisted.python import log
from trigger.conf import settings
from trigger.utils import network, parse_node_port
from trigger.utils.url import parse_url
from trigger import changemgmt, exceptions, rancid
from UserDict import DictMixin
import xml.etree.cElementTree as ET
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
    device_data = _munge_source_data(data_source=data_source)

    # Populate AclsDB if `with_acls` is set
    if with_acls:
        log.msg("NetDevices ACL associations: ENABLED")
        aclsdb = AclsDB()
    else:
        log.msg("NetDevices ACL associations: DISABLED")
        aclsdb = None

    # Populate `netdevices` dictionary with `NetDevice` objects!
    for obj in device_data:
        dev = NetDevice(data=obj, with_acls=aclsdb)

        # Only return devices with adminStatus of 'PRODUCTION' unless
        # `production_only` is True
        if dev.adminStatus != 'PRODUCTION' and production_only:
            #log.msg('DEVICE NOT PRODUCTION')
            continue

        # These checks should be done on generation of netdevices.xml.
        # Skip empty nodenames
        if dev.nodeName is None:
            continue

        # Add to dict
        netdevices[dev.nodeName] = dev

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
        self.manufacturer = None
        self.vendor = None
        self.model = None
        self.serialNumber = None

        # Administrivia
        self.adminStatus = None
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
            self.vendor in ('a10', 'arista', 'aruba', 'cisco', 'force10'),
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
        def disable_paging_brocade():
            """Brocade commands differ by platform."""
            if self.is_brocade_vdx():
                return ['terminal length 0']
            else:
                return ['skip-page-display']

        # Commands used to disable paging.
        default = ['terminal length 0']
        paging_map = {
            'a10': default,
            'arista': default,
            'aruba': ['no paging'], # v6.2.x this is not necessary
            'brocade': disable_paging_brocade(), # See comments above
            'cisco': default,
            'dell': ['terminal datadump'],
            'f5': ['modify cli preference pager disabled'],
            'force10': default,
            'foundry': ['skip-page-display'],
            'juniper': ['set cli screen-length 0'],
            'mrv': ['no pause'],
            'netscreen': ['set console page 0'],
            'paloalto': ['set cli scripting-mode on', 'set cli pager off'],
        }

        cmds = paging_map.get(self.vendor.name)
        if self.is_netscreen():
            cmds = paging_map['netscreen']

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
        elif self.make and 'nexus' in self.make.lower():
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

    def is_netscreen(self):
        """Am I a NetScreen running ScreenOS?"""
        # Are we even a firewall?
        if not self.is_firewall():
            return False

        # If vendor or make is netscreen, automatically True
        if self.vendor == 'netscreen' or self.make.lower() == 'netscreen':
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
        def __init__(self, production_only, with_acls):
            self._dict = {}
            _populate(netdevices=self._dict,
                      data_source=settings.NETDEVICES_SOURCE,
                      production_only=production_only, with_acls=with_acls)

        def __getitem__(self, key):
            return self._dict[key]

        def keys(self):
            return self._dict.keys()

        def find(self, key):
            """
            Return either the exact nodename, or a unique dot-delimited
            prefix.  For example, if there is a node 'test1-abc.net.aol.com',
            then any of find('test1-abc') or find('test1-abc.net') or
            find('test1-abc.net.aol.com') will match, but not find('test1').

            :param string key: Hostname prefix to find.
            :returns: NetDevice object
            """
            if key in self._dict:
                return self._dict[key]

            matches = [x for x in self._dict.keys() if x.startswith(key+'.')]

            if matches:
                return self._dict[matches[0]]
            raise KeyError(key)

        def all(self):
            """Returns all NetDevice objects."""
            return self._dict.values()

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

            Example by reference::

                >>> nd = NetDevices()
                >>> myargs = {'onCallName':'Data Center', 'model':'FCSLB'}
                >>> mydevices = nd(**myargs)

            Example by keyword arguments::

                >>> mydevices = nd(oncallname='data center', model='fcslb')

            :returns: List of NetDevice objects
            """
            # Only build the lower-to-regular mapping once per instance and
            # only on the first time .match() is called.
            if not hasattr(self, '_device_key_map'):
                mydev = self.all()[0]
                dev_data = vars(mydev)
                key_map = {}
                for key in dev_data:
                    key_map[key.lower()] = key

                self._device_key_map = key_map

            def attr(key):
                """Helper function for the lowercase to regular attribute mapping."""
                return self._device_key_map[key]

            # Here we build a list comprehension and then eval it at the end.
            query_prefix = "[dev for dev in self.all() if "
            query_suffix = "]"
            template = "'%s'.lower() in getattr(dev, attr('%s')).lower()"
            list_body = ' and '.join(template % (v,k.lower()) for k,v in kwargs.iteritems())
            list_comp = query_prefix + list_body + query_suffix

            # This was for the case-sensitive version
            #template = "'%s' in dev.%s"
            #list_body = ' and '.join(template % (v,k) for k,v in kwargs.iteritems())

            return eval(list_comp)

        def get_devices_by_type(self, devtype):
            """
            Returns a list of NetDevice objects with deviceType matching type.

            Known deviceTypes: ['FIREWALL', 'ROUTER', 'SWITCH']
            """
            return [x for x in self._dict.values() if x.deviceType == devtype]

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
        if NetDevices._Singleton is None:
            NetDevices._Singleton = NetDevices._actual(production_only=production_only,
                                                       with_acls=with_acls)

    def __getattr__(self, attr):
        return getattr(NetDevices._Singleton, attr)

    def __setattr__(self, attr, value):
        return setattr(NetDevices._Singleton, attr, value)
