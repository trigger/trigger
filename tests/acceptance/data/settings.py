# -*- coding: utf-8 -*-

# This is a sample settings.py that varies slightly from the default. Please see docs/configuration.rst or
# trigger/conf/global_settings.py for the complete list of default settings.

import IPy
import os
import socket

#===============================
# Global Settings
#===============================

# This is where Trigger should look for its files.
PREFIX = '/etc/trigger'

# Set to True to enable GPG Authentication
# Set to False to use the old .tackf encryption method.
# Should be False unless instructions/integration is ready for GPG
USE_GPG_AUTH = False

# This is used for old auth method. It sucks and needs to die.
# TODO (jathan): This is deprecated. Remove all references to this and make GPG
# the default and only method.
TACACSRC_KEYFILE = os.path.join(PREFIX, '.tackf')
TACACSRC_PASSPHRASE = 'bacon is awesome, son.' # NYI

# Default login realm to store user credentials (username, password) for
# general use within the .tacacsrc
DEFAULT_REALM = 'aol'

# Location of firewall policies
FIREWALL_DIR = '/data/firewalls'

# Location of tftproot.
TFTPROOT_DIR = '/data/tftproot'

# Add internally owned networks here. All network blocks owned/operated and
# considered part of your network should be included.
INTERNAL_NETWORKS = [
    IPy.IP("10.0.0.0/8"),
    IPy.IP("172.16.0.0/12"),
    IPy.IP("192.168.0.0/16"),
]

# The tuple of supported vendors derived from the values of VENDOR_MAP
SUPPORTED_VENDORS = (
    'a10',
    'arista',
    'brocade',
    'cisco',
    'citrix',
    'dell',
    'foundry',
    'juniper',
    'netscreen'
)
VALID_VENDORS = SUPPORTED_VENDORS # For backwards compatibility

# A mapping of manufacturer attribute values to canonical vendor name used by
# Trigger. These single-word, lowercased canonical names are used throughout
# Trigger.
#
# If your internal definition differs from the UPPERCASED ones specified below
# (which they probably do, customize them here.
VENDOR_MAP = {
    'A10 NETWORKS': 'a10',
    'ARISTA NETWORKS': 'arista',
    'BROCADE': 'brocade',
    'CISCO SYSTEMS': 'cisco',
    'CITRIX': 'citrix',
    'DELL': 'dell',
    'FOUNDRY': 'foundry',
    'JUNIPER': 'juniper',
    'NETSCREEN TECHNOLOGIES': 'netscreen',
}

# A dictionary keyed by manufacturer name containing a list of the device types
# for each that is officially supported by Trigger.
SUPPORTED_PLATFORMS = {
    'a10': ['SWITCH'],
    'arista': ['SWITCH'],                         # Your "Cloud" network vendor
    'brocade': ['ROUTER', 'SWITCH'],
    'cisco': ['FIREWALL', 'ROUTER', 'SWITCH'],
    'citrix': ['SWITCH'],                         # Assumed to be NetScalers
    'dell': ['SWITCH'],
    'foundry': ['ROUTER', 'SWITCH'],
    'juniper': ['FIREWALL', 'ROUTER', 'SWITCH'],  # Any devices running Junos
    'netscreen': ['FIREWALL'],                    # Pre-Juniper NetScreens
}

# The tuple of support device types
SUPPORTED_TYPES = ('FIREWALL', 'ROUTER', 'SWITCH')

# A mapping of of vendor names to the default device type for each in the
# event that a device object is created and the deviceType attribute isn't set
# for some reason.
DEFAULT_TYPES = {
    'a10': 'SWITCH',
    'arista': 'SWITCH',
    'brocade': 'SWITCH',
    'citrix': 'SWITCH',
    'cisco': 'ROUTER',
    'dell': 'SWITCH',
    'foundry': 'SWITCH',
    'juniper': 'ROUTER',
    'netscreen': 'FIREWALL',
}

# When a vendor is not explicitly defined within `DEFAULT_TYPES`, fallback to
# this type.
FALLBACK_TYPE = 'ROUTER'

#===============================
# Twister
#===============================

# Default timeout in seconds for commands executed during a session.  If a
# response is not received within this window, the connection is terminated.
DEFAULT_TIMEOUT = 5 * 60

# Default timeout in seconds for initial telnet connections. 
TELNET_TIMEOUT  = 60

# Whether or not to allow telnet fallback
TELNET_ENABLED = True

# A mapping of vendors to the types of devices for that vendor for which you
# would like to disable interactive (pty) SSH sessions, such as when using
# bin/gong.
SSH_PTY_DISABLED = {
    'dell': ['SWITCH'],    # Dell SSH is just straight up broken
}

# A mapping of vendors to the types of devices for that vendor for which you
# would like to disable asynchronous (NON-interactive) SSH sessions, such as
# when using twister or Commando to remotely control a device.
SSH_ASYNC_DISABLED = {
    'arista': ['SWITCH'],  # Known not to work w/ SSH ... yet
    'brocade': ['SWITCH'], # Namely the Brocade VDX =(
    'dell': ['SWITCH'],    # Dell SSH is just straight up broken
}

# Vendors that basically just emulate Cisco's IOS and can be treated
# accordingly for the sake of interaction.
IOSLIKE_VENDORS = (
    'a10',
    'arista',
    'brocade',
    'cisco',
    'dell',
    'foundry',
)

#===============================
# NetDevices
#===============================

# Path to the explicit module file for autoacl.py so that we can still perform
# 'from trigger.acl.autoacl import autoacl' without modifying sys.path.
AUTOACL_FILE = os.environ.get('AUTOACL_FILE', os.path.join(PREFIX, 'autoacl.py'))

# A tuple of data loader classes, specified as strings. Optionally, a tuple can
# be used instead of a string. The first item in the tuple should be the
# Loader's module, subsequent items are passed to the Loader during
# initialization.
NETDEVICES_LOADERS = (
    'trigger.netdevices.loaders.filesystem.XMLLoader',
    'trigger.netdevices.loaders.filesystem.JSONLoader',
    'trigger.netdevices.loaders.filesystem.SQLiteLoader',
    'trigger.netdevices.loaders.filesystem.CSVLoader',
    'trigger.netdevices.loaders.filesystem.RancidLoader',
    # Example of a database loader where the db information is sent along as an
    # argument. The args can be anything you want.
    #['trigger.netdevices.loaders.mysql.Loader', {'dbuser': 'root', 'dbpass': 'abc123', 'dbhost': 'localhost', 'dbport': 3306}, 'bacon'],
)

# A path or URL to netdevices device metadata source data, which is used to
# populate trigger.netdevices.NetDevices. For more information on this, see
# NETDEVICES_LOADERS.
NETDEVICES_SOURCE = os.environ.get('NETDEVICES_SOURCE', os.path.join(PREFIX, 'netdevices.xml'))

# Assign NETDEVICES_SOURCE to NETDEVICES_FILE for backwards compatibility
NETDEVICES_FILE = NETDEVICES_SOURCE

# Whether to treat the RANCID root as a normal instance, or as the root to
# multiple instances. This is only checked when using RANCID as a data source.
RANCID_RECURSE_SUBDIRS = os.environ.get('RANCID_RECURSE_SUBDIRS', False)

# Valid owning teams (e.g. device.owningTeam) go here. These are examples and should be
# changed to match your environment.
VALID_OWNERS = (
    'Data Center',
    'Backbone Engineering',
    'Enterprise Networking',
)

# Fields and values defined here will dictate which Juniper devices receive a#
# ``commit-configuration full`` when populating ``NetDevice.commit_commands`.#
# The fields and values must match the objects exactly or it will fallback to
# ``commit-configuration``.
JUNIPER_FULL_COMMIT_FIELDS = {
    'deviceType': 'SWITCH',
    'make': 'EX4200',
}

#===============================
# Bounce Windows/Change Mgmt
#===============================

# Path of the explicit module file for bounce.py containing custom bounce
# window mappings.
BOUNCE_FILE = os.environ.get('BOUNCE_FILE', os.path.join(PREFIX, 'bounce.py'))

# Default bounce timezone. All BounceWindow objects are configured using
# US/Eastern for now.
BOUNCE_DEFAULT_TZ = 'US/Eastern'

# The default fallback window color for bounce windows. Must be one of
# ('green', 'yellow', or 'red').
#
#     green: Low risk
#    yellow: Medium risk
#       red: High risk
BOUNCE_DEFAULT_COLOR = 'red'

#===============================
# Redis Settings
#===============================

# Redis master server. This will be used unless it is unreachable.
REDIS_HOST = '127.0.0.1'

# The Redis port. Default is 6379.
REDIS_PORT = 6379

# The Redis DB. Default is 0.
REDIS_DB = 0

#===============================
# Database Settings
#===============================

# These are self-explanatory, I hope.
# TODO (jathan): Replace remaining db interaction w/ Redis.
DATABASE_NAME = 'trigger'
DATABASE_USER = 'trigger'
DATABASE_PASSWORD = 'abc123'
DATABASE_HOST = '127.0.0.1'
DATABASE_PORT = 3306

#===============================
# ACL Management
#===============================
# FILTER names of ACLs that should be skipped or ignored by tools
# NOTE: These should be the names of the filters as they appear on devices. We
# want this to be mutable so it can be modified at runtime.
# TODO (jathan): Move this into Redis and maintain with 'acl' command?
IGNORED_ACLS = [
    'netflow', 
    'massive-edge-filter',
    'antispoofing',
]

# FILE names ACLs that shall not be modified by tools
# NOTE: These should be the names of the files as they exist in FIREWALL_DIR.
# Trigger expects ACLs to be prefixed with 'acl.'.  These are examples and
# should be replaced.
NONMOD_ACLS  = [ 
    'acl.netflow', 
    'acl.antispoofing',
    'acl.border-protect',
    'acl.route-engine-protect',
]

# Mapping of real IP to external NAT. This is used by load_acl in the event
# that a TFTP or connection from a real IP fails or explicitly when passing the
# --no-vip flag.
# format: {local_ip: external_ip}
VIPS = {
    '10.20.21.151': '5.60.17.81',
    '10.10.18.157': '5.60.71.81',
}

#===============================
# ACL Loading/Rate-Limiting
#===============================
# All of the following settings are currently only used in ``load_acl``.  If
# and when the load_acl functionality gets moved into the API, this might
# change.

# Any FILTER name (not filename) in this list will be skipped during automatic loads.
AUTOLOAD_BLACKLIST = [
    'route-engine-protect',
    'netflow', 
    'antispoofing',
    'static-policy',
    'border-protect',
]

# Assign blacklist to filter for backwards compatibility
AUTOLOAD_FILTER = AUTOLOAD_BLACKLIST

# Modify this if you want to create a list that if over the specified number of
# routers will be treated as bulk loads.
# TODO (jathan): Provide examples so that this has more context/meaning. The
# current implementation is kind of broken and doesn't scale for data centers
# with a large of number of devices.
AUTOLOAD_FILTER_THRESH = {
    'route-engine-protect':3,
    'antispoofing':5,
    '12345':10,
}

# Any ACL applied on a number of devices >= to this number will be treated as
# bulk loads.
AUTOLOAD_BULK_THRESH = 10

# Add an acl:max_hits here if you want to override BULK_MAX_HITS_DEFAULT
# Keep in mind this number is PER EXECUTION of load_acl --auto (typically once
# per hour or 3 per bounce window).
#
# 1 per load_acl execution; ~3 per day, per bounce window
# 2 per load_acl execution; ~6 per day, per bounce window
# etc.
BULK_MAX_HITS = {
    'abc123': 3,
    'xyz246': 5,
    'border-protect': 5,
}

# If an ACL is bulk but not in BULK_MAX_HITS, use this number as max_hits
BULK_MAX_HITS_DEFAULT = 1

#===============================
# OnCall Engineer Display
#===============================
# This variable should be a function that returns data for your on-call engineer, or
# failing that None.  The function should return a dictionary that looks like
# this:
#
# {'username': 'joegineer', 
#  'name': 'Joe Engineer', 
#  'email': 'joe.engineer@example.notreal'}
def get_current_oncall():
    """fetch current on-call info"""
    # from somewhere import get_primary_oncall()

    try:
        ret = get_primary_oncall()
    except:
        return None

    return ret

# If you don't want to return this information, have it return None.
GET_CURRENT_ONCALL = lambda x=None: x
#GET_CURRENT_ONCALL = get_current_oncall

#===============================
# CM Ticket Creation
#===============================
# This should be a function that creates a CM ticket and returns the ticket
# number, or None. 
# TODO (jathan): Improve this interface so that it is more intuitive.
def create_cm_ticket(acls, oncall, service='load_acl'):
    """Create a CM ticket and return the ticket number or None"""
    # from somewhere import create_cm_ticket

    devlist = ''
    for dev, aclset in acls.items():
        a = sorted(aclset)
        devlist += "%-32s %s\n" % (dev, ' '.join(a))
        
    oncall['devlist'] = devlist
    oncall['service'] = service

    return create_ticket(**oncall)

def _create_cm_ticket_stub(**args):
    return None

# If you don't want to use this feature, just have the function return None.
#CREATE_CM_TICKET = lambda a=None o, s: None
CREATE_CM_TICKET = _create_cm_ticket_stub

#===============================
# Notifications
#===============================
# Email sender for integrated toosl. Usually a good idea to make this a
# no-reply address.
EMAIL_SENDER = 'nobody@not.real'

# Who to email when things go well (e.g. load_acl --auto)
SUCCESS_EMAILS = [
    #'neteng@example.com',
]

# Who to email when things go not well (e.g. load_acl --auto)
FAILURE_EMAILS = [
    #'primarypager@example.com',
    #'secondarypager@example.com',
]

# The default sender for integrated notifications. This defaults to the fqdn
# for the localhost.
NOTIFICATION_SENDER = socket.gethostname()

# Destinations (hostnames, addresses) to notify when things go well.
SUCCESS_RECIPIENTS = [
    # 'foo.example.com',
]

# Destinations (hostnames, addresses) to notify when things go not well.
FAILURE_RECIPIENTS = [
    # socket.gethostname(), # The fqdn for the localhost
]

# This is a list of fully-qualified paths. Each path should end with a callable
# that handles a notification event and returns ``True`` in the event of a
# successful notification, or ``None``.
NOTIFICATION_HANDLERS = [
    'trigger.utils.notifications.handlers.email_handler',
]
