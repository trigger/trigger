# -*- coding: utf-8 -*-

"""
Redis-based replacement of the legacy acls.db file. This is used for
interfacing with the explicit and automatic ACL-to-device mappings.

>>> from trigger.netdevices import NetDevices
>>> from trigger.acl.db import AclsDB
>>> nd = NetDevices()
>>> dev = nd.find('test1-abc')
>>> a = AclsDB()
>>> a.get_acl_set(dev)
set(['juniper-router.policer', 'juniper-router-protect', 'abc123'])
>>> a.get_acl_set(dev, 'explicit')
set(['abc123'])
>>> a.get_acl_set(dev, 'implicit')
set(['juniper-router.policer', 'juniper-router-protect'])
>>> a.get_acl_dict(dev)
{'all': set(['abc123', 'juniper-router-protect', 'juniper-router.policer']),
 'explicit': set(['abc123']),
  'implicit': set(['juniper-router-protect', 'juniper-router.policer'])}
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan@gmail.com'
__copyright__ = 'Copyright 2010-2012, AOL Inc.; 2013 Salesforce.com'

from collections import defaultdict
import redis
import sys

from twisted.python import log
from trigger.acl.autoacl import autoacl
from trigger import exceptions
from trigger.conf import settings


ACLSDB_BACKUP = './acls.csv'
DEBUG = False

# The redis instance. It doesn't care if it can't reach Redis until you actually
# try to talk to Redis.
r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT,
                db=settings.REDIS_DB)

# Exports
__all__ = (
    # functions
    'get_matching_acls',
    'get_all_acls',
    'get_bulk_acls',
    'populate_bulk_acls',

    # classes
    'AclsDB',
)


# Classes
class AclsDB(object):
    """
    Container for ACL operations.

    add/remove operations are for explicit associations only.
    """
    def __init__(self):
        self.redis = r
        log.msg('ACLs database client initialized')

    def add_acl(self, device, acl):
        """
        Add explicit acl to device

        >>> dev = nd.find('test1-mtc')
        >>> a.add_acl(dev, 'acb123')
        'added acl abc123 to test1-mtc.net.aol.com'
        """
        try:
            rc = self.redis.sadd('acls:explicit:%s' % device.nodeName, acl)
        except redis.exceptions.ResponseError as err:
            return str(err)
        if rc != 1:
            raise exceptions.ACLSetError('%s already has acl %s' % (device.nodeName, acl))
        self.redis.save()

        return 'added acl %s to %s' % (acl, device)

    def remove_acl(self, device, acl):
        """
        Remove explicit acl from device.

        >>> a.remove_acl(dev, 'acb123')
        'removed acl abc123 from test1-mtc.net.aol.com'
        """
        try:
            rc = self.redis.srem('acls:explicit:%s' % device.nodeName, acl)
        except redis.exceptions.ResponseError as err:
            return str(err)
        if rc != 1:
            raise exceptions.ACLSetError('%s does not have acl %s' % (device.nodeName, acl))
        self.redis.save()

        return 'removed acl %s from %s' % (acl, device)

    def get_acl_dict(self, device):
        """
        Returns a dict of acl mappings for a @device, which is expected to
        be a NetDevice object.

        >>> a.get_acl_dict(dev)
        {'all': set(['115j', 'protectRE', 'protectRE.policer', 'test-bluej',
        'testgreenj', 'testops_blockmj']),
        'explicit': set(['test-bluej', 'testgreenj', 'testops_blockmj']),
        'implicit': set(['115j', 'protectRE', 'protectRE.policer'])}
        """
        acls = {}

        # Explicit (we want to make sure the key exists before we try to assign
        # a value)
        expl_key = 'acls:explicit:%s' % device.nodeName
        if self.redis.exists(expl_key):
            acls['explicit'] = self.redis.smembers(expl_key) or set()
        else:
            acls['explicit'] = set()

        # Implicit (automatically-assigned). We're passing the explicit_acls to
        # autoacl so that we can use them logically for auto assignments.
        acls['implicit'] = autoacl(device, explicit_acls=acls['explicit'])

        # All
        acls['all'] = acls['implicit'] | acls['explicit']

        return acls

    def get_acl_set(self, device, acl_set='all'):
        """
        Return an acl set matching @acl_set for a given device.  Match can be
        one of ['all', 'explicit', 'implicit']. Defaults to 'all'.

        >>> a.get_acl_set(dev)
        set(['testops_blockmj', 'testgreenj', '115j', 'protectRE',
        'protectRE.policer', 'test-bluej'])
        >>> a.get_acl_set(dev, 'explicit')
        set(['testops_blockmj', 'test-bluej', 'testgreenj'])
        >>> a.get_acl_set(dev, 'implicit')
        set(['protectRE', 'protectRE.policer', '115j'])
        """
        acls_dict = self.get_acl_dict(device)
        #ACL_SETS = ['all', 'explicit', 'implicit', 'bulk']
        ACL_SETS = acls_dict.keys()
        if DEBUG: print 'fetching', acl_set, 'acls for', device
        if acl_set not in ACL_SETS:
            raise exceptions.InvalidACLSet('match statement must be one of %s' % ACL_SETS)

        return acls_dict[acl_set]


# Functions
def populate_explicit_acls(aclsdb_file):
    """
    populate acls:explicit from legacy acls.db file.

    Format:

    '{unused},{hostname},{acls}\\n'

    - @unused is leftover from legacy and is not used
    - @hostname column is the fqdn of the device
    - @acls is a colon-separated list of ACL names

    Example:

    xx,test1-abc.net.aol.com,juniper-router.policer:juniper-router-protect:abc123
    xx,test2-abc.net.aol.com,juniper-router.policer:juniper-router-protect:abc123
    """
    import csv
    for row in csv.reader(open(aclsdb_file)):
        if not row[0].startswith('!'):
            [r.sadd('acls:explicit:%s' % row[1], acl) for acl in row[2].split(':')]
    r.save()

def backup_explicit_acls():
    """dumps acls:explicit:* to csv"""
    import csv
    out = csv.writer(file(ACLSDB_BACKUP, 'w'))
    for key in r.keys('acls:explicit:*'):
        out.writerow([key.split(':')[-1], ':'.join(map(str, r.smembers(key)))])

def populate_implicit_acls(nd=None):
    """populate acls:implicit (autoacls)"""
    nd = nd or get_netdevices()
    for dev in nd.all():
        [r.sadd('acls:implicit:%s' % dev.nodeName, acl) for acl in autoacl(dev)]
    r.save()

def get_netdevices(production_only=True, with_acls=True):
    """Shortcut to import, instantiate, and return a NetDevices instance."""
    from trigger.netdevices import NetDevices
    return NetDevices(production_only=production_only, with_acls=with_acls)

def get_all_acls(nd=None):
    """
    Returns a dict keyed by acl names whose containing a set of NetDevices
    objects to which each acl is applied.

    @nd can be your own NetDevices object if one is not supplied already

    >>> all_acls = get_all_acls()
    >>> all_acls['abc123']
    set([<NetDevice: test1-abc.net.aol.com>, <NetDevice: fw1-xyz.net.aol.com>])
    """
    #nd = nd or settings.get_netdevices()
    nd = nd or get_netdevices()
    all_acls = defaultdict(set)
    for device in nd.all():
        [all_acls[acl].add(device) for acl in device.acls if acl != '']

    return all_acls

def get_bulk_acls(nd=None):
    """
    Returns a set of acls with an applied count over
    settings.AUTOLOAD_BULK_THRESH.
    """
    #nd = nd or settings.get_netdevices()
    nd = nd or get_netdevices()
    all_acls = get_all_acls()
    bulk_acls = set([acl for acl, devs in all_acls.items() if
                     len(devs) >= settings.AUTOLOAD_BULK_THRESH])

    return bulk_acls

def populate_bulk_acls(nd=None):
    """
    Given a NetDevices instance, Adds bulk_acls attribute to NetDevice objects.
    """
    nd = nd or get_netdevices()
    bulk_acls = get_bulk_acls()
    for dev in nd.all():
        dev.bulk_acls = dev.acls.intersection(bulk_acls)

def get_matching_acls(wanted, exact=True, match_acl=True, match_device=False, nd=None):
    """
    Return a sorted list of the names of devices that have at least one
    of the wanted ACLs, and the ACLs that matched on each.  Without 'exact',
    match ACL name by startswith.

    To get a list of devices, matching the ACLs specified:

    >>> adb.get_matching_acls(['abc123'])
    [('fw1-xyz.net.aol.com', ['abc123']), ('test1-abc.net.aol.com', ['abc123'])]

    To get a list of ACLS matching the devices specified using an explicit
    match (default) by setting match_device=True:

    >>> adb.get_matching_acls(['test1-abc'], match_device=True)
    []
    >>> adb.get_matching_acls(['test1-abc.net.aol.com'], match_device=True)
    [('test1-abc.net.aol.com', ['abc123', 'juniper-router-protect',
    'juniper-router.policer'])]

    To get a list of ACLS matching the devices specified using a partial
    match. Not how it returns all devices starting with 'test1-mtc':

    >>> adb.get_matching_acls(['test1-abc'], match_device=True, exact=False)
    [('test1-abc.net.aol.com', ['abc123', 'juniper-router-protect',
    'juniper-router.policer'])]
    """
    found = []
    wanted_set = set(wanted)

    def match_exact(x):
        return x & wanted_set

    def match_begin(x):
        matched = set()
        for a in wanted_set:
            for b in x:
                if b.startswith(a):
                    matched.add(b)
        return matched

    match = exact and match_exact or match_begin

    # Return all the ACLs if matched by device, or the matched ACLs
    # if matched by ACL.
    #nd = nd or settings.get_netdevices()
    nd = nd or get_netdevices()
    for name, dev in nd.iteritems():
        hit = None
        if match_device:
            if exact and name in wanted:
                hit = dev.acls
            elif not exact:
                for x in wanted:
                    if name.startswith(x):
                        hit = dev.acls
                        break

        if hit is None and match_acl:
            hit = match(dev.acls)

        if hit:
            matched = list(hit)
            matched.sort()
            found.append((name, matched))

    found.sort()
    return found
