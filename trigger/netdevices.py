# -*- coding: utf-8 -*-

"""
The heart and soul of Trigger, NetDevices is an abstract interface to network device metadata
and ACL associations.

Parses netdevices.xml and makes available a dictionary of :class:`~trigger.netdevices.NetDevice`
objects, which is keyed by the FQDN of every network device.

Other interfaces are non-public.

Example::

    >>> from trigger.netdevices import NetDevices
    >>> nd = NetDevices()
    >>> dev = nd['test1-abc.net.aol.com']
    >>> dev.manufacturer, dev.make
    ('JUNIPER', 'MX960-BASE-AC')
    >>> dev.bounce.next_ok('green')
    datetime.datetime(2010, 4, 9, 9, 0, tzinfo=<UTC>)

"""

__author__ = 'Jathan McCollum, Eileen Tschetter, Mark Thomas, Michael Shields'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2006-2011, AOL Inc.'

# Imports (duh?)
import itertools
import os
import sqlite3 as sqlite
import sys
import time
from UserDict import DictMixin
from xml.etree.cElementTree import ElementTree, parse
from trigger.conf import settings
from trigger.changemgmt import site_bounce, BounceStatus
from trigger.acl.db import AclsDB

try:
    import simplejson as json # Prefer simplejson because of SPEED!
except ImportError:
    import json


# Constants
SUPPORTED_FORMATS = ('xml', 'json', 'sqlite')


# Exports
__all__ = ['device_match', 'NetDevice', 'NetDevices']


# Functions
def _parse_json(data_source):
    """
    Parse 'netdevices.json' and return list of JSON objects.

    :param data_source: Absolute path to data file
    """
    with open(data_source, 'r') as contents:
         # TODO (jathan): Can we somehow return an generator like the other
         # _parse methods? Maybe using JSONDecoder?
         data = json.load(contents)

    return data

def _parse_xml(data_source):
    """
    Parse 'netdevices.xml' and return a list of node 2-tuples (key, value).
    These are as good as a dict without the extra dict() call.

    :param data_source: Absolute path to data file
    """
    # Parsing the complete file into a tree once and extracting outthe device
    # nodes is faster than using iterparse(). Curses!!
    xml = parse(netdevicesxml_file).findall('device')

    # This is a generator within a generator. Trust me, it works in _populate()
    data = (((e.tag, e.text) for e in node.getchildren()) for node in xml)

    return data

def _parse_sqlite(data_source):
    """
    Parse 'netdevices.sql' and return a list of stuff.

    :param data_source: Absolute path to data file
    """
    connection = sqlite.connect(data_source)
    cursor = connection.cursor()

    # Get the column names. This is a simple list strings.
    colfetch  = cursor.execute('pragma table_info(netdevices)')
    results = colfetch.fetchall()
    columns = [r[1] for r in results]

    # And the devices. This is a list of tuples whose values match the indexes
    # of the column names.
    devfetch = cursor.execute('select * from netdevices')
    devrows = devfetch.fetchall()

    # Another generator within a generator, which structurally is a list of
    # lists containing 2-tuples (key, value).
    data = (itertools.izip(columns, row) for row in devrows)

    return data

def _munge_source_data(data_source=settings.NETDEVICES_FILE,
                       format=settings.NETDEVICES_FORMAT):
    """
    Read the source data in the specified format, parse it, and return a
    dictionary of objects.

    :param data_source: Absolute path to source data file
    :param format: One of 'xml', 'json', or 'sqlite'
    """
    assert format in SUPPORTED_FORMATS

    parsers = {
        'xml': _parse_xml,
        'json': _parse_json,
        'sqlite': _parse_sqlite,
    }
    parser = parsers[format]
    data = parser(data_source)

    return data

def _populate(netdevices, data_source, data_format, production_only):
    """
    Populates the NetDevices with NetDevice objects.

    Abstracted from within NetDevices to prevent accidental repopulation of NetDevice
    objects.
    """
    #start = time.time()
    aclsdb = AclsDB()

    device_data = _munge_source_data(data_source=data_source, format=data_format)

    for obj in device_data:
        dev = NetDevice(data=obj)

        # Only return devices with adminStatus of 'PRODUCTION' unless
        # production_only is True
        if dev.adminStatus != 'PRODUCTION' and production_only:
            continue

        # These checks should be done on generation of netdevices.xml.
        ## skip empty nodenames
        if dev.nodeName is None:
            continue

        ## lowercase hostnames
        dev.nodeName = dev.nodeName.lower()

        ## cleanup whitespace from owning team
        dev.owningTeam = dev.owningTeam.strip()

        # Populate the ACLs for each device.
        dev.explicit_acls = dev.implicit_acls = dev.acls = dev.bulk_acls = set()
        acls_dict = aclsdb.get_acl_dict(dev)
        dev.explicit_acls = acls_dict['explicit']
        dev.implicit_acls = acls_dict['implicit']
        dev.acls = acls_dict['all']

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
            #print 'Choice:', choice
            #print 'You chose: %s' % match
        else:
            print "No matches for '%s'." % name

    return match


# Classes
class NetDevice(object):
    """
    Almost all the attributes are populated by netdevices._populate() and are
    mostly dependent upon the source data. This is prone to implementation
    problems and should be revisited in the long-run as there are certain
    fields that are baked into the core functionality of Trigger.

    Users usually won't create `NetDevice` objects directly! Rely instead upon
    `NetDevices` to do this for you.
    """
    def __init__(self, data=None):
        # Here comes all of the bare minimum set of attributes a NetDevice
        # object needs for basic functionality within the existing suite.

        # Hostname
        self.nodeName = None

        # Hardware Info
        self.deviceType = None
        self.make = None
        self.manufacturer = None
        self.model = None
        self.serialNumber = None

        # Administrivia
        self.adminStatus = None
        self.assetID = None
        self.budgetCode = None
        self.budgetName = None
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

        # ACLs
        self.explicit_acls = self.implicit_acls = self.acls = self.bulk_acls = set()

        # And if data has been passed, well... replace everything that was in
        # it.
        if data is None:
            pass
        else:
            self.__dict__.update(data) # Better hope this is a dict!

        # And lowercase the nodeName for completeness.
        if self.nodeName is not None:
            self.nodeName = self.nodeName.lower()

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
        return site_bounce(self.site, oncallid=self.onCallID)

    @property
    def shortName(self):
        return self.nodeName.split('.', 1)[0]

    def allowable(self, action, when=None):
        """
        Ok to perform the specified action? Returns a boolean value. False
        means a bounce window conflict. For now 'load-acl' is the only valid
        action and moratorium status is not checked.
        """
        assert action == 'load-acl'
        return self.bounce.status(when) == BounceStatus('green')

    def next_ok(self, action, when=None):
        """Return the next time at or after the specified time (default now)
        that it will be ok to perform the specified action."""
        assert action == 'load-acl'
        return self.bounce.next_ok(BounceStatus('green'), when)

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
        return all([self.deviceType=='SWITCH', self.manufacturer=='CITRIX'])

    def dump(self):
        """Prints details for a device."""
        dev = self
        print
        print '\tHostname:         ', dev.nodeName
        print '\tOwning Org.:      ', dev.owner
        print '\tOwning Team:      ', dev.owningTeam
        print '\tOnCall Team:      ', dev.onCallName
        print
        print '\tManufacturer:     ', dev.manufacturer
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

class NetDevices(DictMixin):
    """
    Returns an immutable Singleton dictionary of
    :class:`~trigger.netdevices.NetDevice` objects. By default
    it will only return devices for which ``adminStatus=='PRODUCTION'``.

    There are hardly any use cases where ``NON-PRODUCTION`` devices are needed, and
    it can cause real bugs of two sorts:

      1. trying to contact unreachable devices and reporting spurious failures,
      2. hot spares with the same nodeName.

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
        def __init__(self, production_only=True):
            self._dict = {}
            _populate(
                self._dict,
                settings.NETDEVICES_FILE,
                settings.NETDEVICES_FORMAT,
                production_only,
            )

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
                >>> mydevices = nd(**kwargs)

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

            Known deviceTypes: ['FIREWALL', 'ROUTER', 'SWITCH', 'DWDM']
            """
            return [x for x in self._dict.values() if x.deviceType == devtype]

        def list_switches(self):
            """Returns a list of NetDevice objects with deviceType of SWITCH """
            return self.get_devices_by_type('SWITCH')

        def list_routers(self):
            """ Returns a list of NetDevice objects with deviceType of ROUTER """
            return self.get_devices_by_type('ROUTER')

        def list_firewalls(self):
            """ Returns a list of NetDevice objects with deviceType of FIREWALL """
            return self.get_devices_by_type('FIREWALL')

    def __init__(self, production_only=True):
        if NetDevices._Singleton is None:
            NetDevices._Singleton = NetDevices._actual(production_only=production_only)

    def __getattr__(self, attr):
        return getattr(NetDevices._Singleton, attr)

    def __setattr__(self, attr, value):
        return setattr(NetDevices._Singleton, attr, value)
