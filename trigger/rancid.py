#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Parse RANCID db files so they can be converted into Trigger NetDevice objects.

.. versionadded:: 1.2

Far from complete. Very early in development. Here is a basic example.

    >>> from trigger import rancid
    >>> rancid_root = '/path/to/rancid/data'
    >>> r = Rancid(rancid_root)
    >>> dev = r.devices.get('test1-abc.net.aol.com')
    >>> dev
    RancidDevice(nodeName='test-abc.net.aol.com', manufacturer='juniper', deviceStatus='up', deviceType=None)

Another option if you want to get the parsed RANCID data directly without
having to create an object is as simple as this::

    >>> parsed = rancid.parse_rancid_data('/path/to/dancid/data')

Or using multiple RANCID instances within a single root::

    >>> multi_parsed = rancid.parse_rancid_data('/path/to/rancid/data', recurse_subdirs=True)

"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2012-2012, AOL Inc.; 2013 Salesforce.com'
__version__ = '0.1.1'

import collections
import copy
import csv
import datetime
import itertools
import os
import sys

__all__ = ('parse_rancid_file', 'parse_devices', 'walk_rancid_subdirs',
           'parse_rancid_data', 'gather_devices', 'Rancid', 'RancidDevice')

# Constants
CONFIG_DIRNAME = 'configs'
RANCID_DB_FILE = 'router.db'
RANCID_ALL_FILE = 'routers.all'
RANCID_DOWN_FILE = 'routers.down'
RANCID_UP_FILE = 'routers.up'
NETDEVICE_FIELDS = ['nodeName', 'manufacturer', 'deviceStatus', 'deviceType']


# Functions
def _parse_delimited_file(root_dir, filename, delimiter=':'):
    """
    Parse a colon-delimited file and return the contents as a list of lists.

    Intended to be used for parsing of all RANCID files.

    :param root_dir:
        Where to find the file

    :param filename:
        Name of the file to parse

    :param delimiter:
        (Optional) Field delimiter
    """
    filepath = os.path.join(root_dir, filename)
    with open(filepath, 'r') as f:
        reader = csv.reader(f, delimiter=delimiter)
        return [r for r in reader if len(r) > 1] # Skip unparsed lines

    return None

def parse_rancid_file(rancid_root, filename=RANCID_DB_FILE, fields=None,
                      delimiter=':'):
    """
    Parse a RANCID file and return generator representing a list of lists
    mapped  to the ``fields``.

    :param rancid_root:
        Where to find the file

    :param filename:
        Name of the file to parse (e.g. ``router.db``)

    :param fields:
        (Optional) A list of field names used to map to the device data

    :param delimiter:
        (Optional) Field delimiter
    """
    device_data = _parse_delimited_file(rancid_root, filename, delimiter)
    if not device_data:
        return None # Always return None if there are no results

    # Make sure fields is not null and is some kind of iterable
    if not fields:
        fields = NETDEVICE_FIELDS
    else:
        if not isinstance(fields, collections.Iterable):
            raise RuntimeError('`fields` must be iterable')

    # Map fields to generator of generators (!!)
    metadata = (itertools.izip_longest(fields, vals) for vals in device_data)

    return metadata

def walk_rancid_subdirs(rancid_root, config_dirname=CONFIG_DIRNAME,
                        fields=None):
    """
    Walk the ``rancid_root`` and parse the included RANCID files.

    Returns a dictionary keyed by the name of the subdirs with values set to
    the parsed data for each RANCID file found inside.

        >>> from trigger import rancid
        >>> subdirs = rancid.walk_rancid_subdirs('/data/rancid')
        >>> subdirs.get('network-security')
        {'router.db': <generator object <genexpr> at 0xa5b852c>,
         'routers.all': <generator object <genexpr> at 0xa5a348c>,
         'routers.down': <generator object <genexpr> at 0xa5be9dc>,
         'routers.up': <generator object <genexpr> at 0xa5bea54>}

    :param rancid_root:
        Where to find the file

    :param config_dirname:
        If the 'configs' dir is named something else

    :param fields:
        (Optional) A list of field names used to map to the device data
    """
    walker = os.walk(rancid_root)
    baseroot, basedirs, basefiles = walker.next() # First item is base

    results = {}
    for root, dirnames, filenames in walker:
        # Skip any path with CVS in it
        if 'CVS' in root:
            #print 'skipping CVS:', root
            continue

        # Don't visit CVS directories
        if 'CVS' in dirnames:
            dirnames.remove('CVS')

        # Skip directories with nothing in them
        if not filenames or not dirnames:
            continue

        # Only walk directories in which we also have configs
        if config_dirname in dirnames:
            owner = os.path.basename(root)
            results[owner] = {}
            for file_ in filenames:
                results[owner][file_] = parse_rancid_file(root, file_, fields)

    return results

def parse_rancid_data(rancid_root, filename=RANCID_DB_FILE, fields=None,
                      config_dirname=CONFIG_DIRNAME, recurse_subdirs=False):
    """
    Parse single or multiple RANCID instances and return an iterator of the
    device metadata.

    A single instance expects to find 'router.db' in ``rancid_root``.

    If you set ``recurise_subdirs``, multiple instances will be expected, and a
    `router.db` will be expected to be found in each subdirectory.

    :param rancid_root:
        Where to find the file

    :param filename:
        Name of the file to parse (e.g. ``router.db``)

    :param fields:
        (Optional) A list of field names used to map to the device data

    :param config_dirname:
        If the 'configs' dir is named something else

    :param recurse_subdirs:
        Whether to recurse directories (e.g. multiple instances)
    """
    if recurse_subdirs:
        subdirs = walk_rancid_subdirs(rancid_root, config_dirname, fields)
        metadata = gather_devices(subdirs, filename)
    else:
        metadata = parse_rancid_file(rancid_root, filename, fields)

    return metadata

def parse_devices(metadata, parser):
    """
    Iterate device ``metadata`` to use ``parser`` to create and return a
    list of network device objects.

    :param metadata:
        A collection of key/value pairs (Generally returned from
        `~trigger.rancid.parse_rancid_file`)

    :param parser:
        A callabale used to create your objects
    """

    # Two tees of `metadata` iterator, in case a TypeError is encountered, we
    # aren't losing the first item.
    md_original, md_backup = itertools.tee(metadata)
    try:
        # Try to parse using the generator (most efficient)
        return [parser(d) for d in md_original]
    except TypeError:
        # Try to parse by unpacking a dict into kwargs
        return [parser(**dict(d)) for d in md_backup]
    except Exception as err:
        # Or just give up
        print "Parser failed with this error: %r" % repr(err)
        return None
    else:
        raise RuntimeError('This should never happen!')

def gather_devices(subdir_data, rancid_db_file=RANCID_DB_FILE):
    """
    Returns a chained iterator of parsed RANCID data, based from the results of
    `~trigger.rancid.walk_rancid_subdirs`.

    This iterator is suitable for consumption by
    `~trigger.rancid.parse_devices` or Trigger's
    `~trigger.netdevices.NetDevices`.

    :param rancid_root:
        Where to find your RANCID files (router.db, et al.)

    :param rancid_db_file:
        If it's named other than ``router.db``
    """
    iters = []
    for rdir, files in subdir_data.iteritems():
        # Only carry on if we find 'router.db' or it's equivalent
        metadata = files.get(rancid_db_file)
        if metadata is None:
            continue

        iters.append(metadata)

    return itertools.chain(*iters)

def _parse_config_file(rancid_root, filename, parser=None,
                       config_dirname=CONFIG_DIRNAME, max_lines=30):
    """Parse device config file for metadata (make, model, etc.)"""
    filepath = os.path.join(rancid_root, config_dirname, filename)
    try:
        with open(filepath, 'r') as f:
            config = []
            for idx, line in enumerate(f):
                if idx >= max_lines:
                    break
    
                if any([line.startswith('#'), line.startswith('!') and len(line) > 2]):
                    config.append(line.strip())

            return config

    except IOError:
        return None

def _parse_config_files(devices, rancid_root, config_dirname=CONFIG_DIRNAME):
    '''Parse multiple device config files'''
    return_data = {}
    for dev in devices:
        return_data[dev.nodeName] = _parse_config_file(rancid_root,
                                                       dev.nodeName,
                                                       config_dirname)
    return return_data

def _parse_cisco(config):
    """NYI - Parse Cisco config to get metadata"""

def _parse_juniper(config):
    """NYI - Parse Juniper config to get metadata"""

def _parse_netscreen(config):
    """NYI - Parse NetScreen config to get metadata"""

def massage_data(device_list):
    """"
    Given a list of objects, try to fixup their metadata based on thse rules.

    INCOMPLETE.
    """
    devices = device_list

    netdevices = {}
    for idx, dev in enumerate(devices):
        if dev.manufacturer == 'netscreen':
            dev.manufacturer = 'juniper'
            dev.deviceType = 'FIREWALL'

        elif dev.manufacturer == 'cisco':
            dev.deviceType= 'ROUTER'

        elif dev.manufacturer == 'juniper':
            dev.deviceType = 'ROUTER'
        else:
            print 'WTF', dev.nodeName, 'requires no massaging!'

        """
        # Asset
        dev.serialNumber = dev.assetID = None
        dev.lastUpdate = datetime.datetime.today()
        """
        netdevices[dev.nodeName] = dev

    return netdevices


# Classes
class RancidDevice(collections.namedtuple("RancidDevice", NETDEVICE_FIELDS)):
    """
    A simple subclass of namedtuple to store contents of parsed RANCID files.

    Designed to support all router.* files. The field names are intended to be
    compatible with Trigger's NetDevice objects.

    :param nodeName:
        Hostname of device

    :param manufacturer:
        Vendor/manufacturer name of device

    :param deviceStatus:
        (Optional) Up/down status of device

    :param deviceType:
        (Optional) The device type... determined somehow
    """
    __slots__ = ()

    def __new__(cls, nodeName, manufacturer, deviceStatus=None, deviceType=None):
        return super(cls, RancidDevice).__new__(cls, nodeName, manufacturer,
                                                deviceStatus, deviceType)

class Rancid(object):
    """
    Holds RANCID data. INCOMPLETE.

    Defaults to a single RANID instance specified as ``rancid_root``. It will
    parse the file found at ``rancid_db_file`` and use this to populate the
    ``devices`` dictionary with instances of ``device_class``.

    If you set ``recurse_subdirs``, it is assumed that ``rancid_root`` holds
    one or more individual RANCID instances and will attempt to walk them,
    parse them, and then aggregate all of the resulting device instances into
    the ``devices`` dictionary.

    Still needs:

    + Config parsing for metadata (make, model, type, serial, etc.)
    + Recursive Config file population/parsing when ``recurse_subdirs`` is set

    :param rancid_root:
        Where to find your RANCID files (router.db, et al.)

    :param rancid_db_file:
        If it's named other than ``router.db``

    :param config_dir:
        If it's named other than ``configs``

    :param device_fields:
        A list of field names used to map to the device data. These must match
        the attributes expected by ``device_class``.

    :param device_class:
        If you want something other than ``RancidDevice``

    :param recurse_subdirs:
        Whether you want to recurse directories.
    """
    def __init__(self, rancid_root, rancid_db_file=RANCID_DB_FILE,
                 config_dirname=CONFIG_DIRNAME, device_fields=None,
                 device_class=None, recurse_subdirs=False):
        if device_class is None:
            device_class = RancidDevice

        self.rancid_root = rancid_root
        self.rancid_db_file = rancid_db_file
        self.config_dirname = config_dirname
        self.device_fields = device_fields
        self.device_class = device_class
        self.recurse_subdirs = recurse_subdirs
        self.configs = {}
        self.data = {}
        self.devices = {}
        self._populate()

    def _populate(self):
        """Fired after init, does all the stuff to populate RANCID data."""
        self._populate_devices()

    def _populate_devices(self):
        """
        Read router.db or equivalent and populate ``devices`` dictionary
        with objects.
        """
        metadata = parse_rancid_data(self.rancid_root,
                                     filename=self.rancid_db_file,
                                     fields=self.device_fields,
                                     config_dirname=self.config_dirname,
                                     recurse_subdirs=self.recurse_subdirs)

        objects = parse_devices(metadata, self.device_class)
        self.devices = dict((d.nodeName, d) for d in objects)

    def _populate_configs(self):
        """NYI - Read configs"""
        self.configs = _parse_config_files(self.devices.itervalues(),
                                           self.rancid_root)

    def _populate_data(self):
        """NYI - Maybe keep the other metadata but how?"""
        #self.data['routers.all'] = parse_rancid_file(root, RANCID_ALL_FILE)
        #self.data['routers.down'] = parse_rancid_file(root, RANCID_DOWN_FILE)
        #self.data['routers.up'] = parse_rancid_file(root, RANCID_UP_FILE)
        pass

    def __repr__(self):
        return 'Rancid(%r, recurse_subdirs=%s)' % (self.rancid_root,
                                                   self.recurse_subdirs)
