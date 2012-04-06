# Default Trigger settings. Override these with settings in the module
# pointed-to by the TRIGGER_SETTINGS environment variable. This is pretty much
# an exact duplication of how Django does this.

import os
import IPy

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
TACACSRC_KEYFILE = os.getenv('TACACSRC_KEYFILE', os.path.join(PREFIX, '.tackf'))
TACACSRC_PASSPHRASE = '' # NYI

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

# Who to email when things go well (e.g. load_acl --auto)
SUCCESS_EMAILS = [
    #'neteng@example.com',
]

# Who to email when things go not well (e.g. load_acl --auto)
FAILURE_EMAILS = [
    #'primarypager@example.com',
    #'secondarypager@example.com',
]

#===============================
# Twister
#===============================

# List of supported vendors. These are what Trigger currently supports.
VALID_VENDORS = (
    'ARISTA NETWORKS',
    'BROCADE',
    'CISCO SYSTEMS',
    'CITRIX',
    'DELL',
    'FOUNDRY',
    'JUNIPER',
)

# Default timeout in seconds for commands executed during a session.  If a response is not
# received within this window, the connection is terminated.
DEFAULT_TIMEOUT = 5 * 60

# Default timeout in seconds for initial telnet connections.
TELNET_TIMEOUT  = 60

# Add manufacturers that support SSH logins here. Only add one if ALL devices of that
# manufacturer have SSH logins enabled. Adding CISCO SYSTEMS to this list will
# require a lot of work! (Don't forget the trailing comma when you add a new entry.)
SSH_TYPES = [
    'ARISTA NETWORKS',        # Your "Cloud" network vendor
    'CITRIX',                 # Makers of NetScalers
    'JUNIPER',                # Any devices running JUNOS
    'NETSCREEN TECHNOLOGIES', # Former maker of NetScreen firewalls (pre-Juniper)
]

# Vendors that basically just emulate Cisco's IOS and can be treated
# accordingly for the sake of interaction.
IOSLIKE_VENDORS = (
    'ARISTA NETWORKS',
    'BROCADE',
    'CISCO SYSTEMS',
    'DELL',
    'FOUNDRY',
)

#===============================
# NetDevices
#===============================

# Path to the explicit module file for autoacl.py so that we can still perform
# 'from trigger.acl.autoacl import autoacl' without modifying sys.path.
AUTOACL_FILE = os.environ.get('AUTOACL_FILE', os.path.join(PREFIX, 'autoacl.py'))

# One of 'xml', 'json', 'sqlite'. This MUST match the actual format of
# NETDEVICES_FILE or it won't work for obvious reasons.
NETDEVICES_FORMAT = os.environ.get('NETDEVICES_FORMAT', 'xml')

# Path to netdevices device metadata source file, which is used to populate
# trigger.netdevices.NetDevices. This may be JSON, XML, or a SQLite3 database.
# You must set NETDEVICES_FORMAT to match the type of data.
NETDEVICES_FILE = os.environ.get('NETDEVICES_FILE', os.path.join(PREFIX, 'netdevices.xml'))

#NETDEVICES_FILE = os.environ.get('NETDEVICES_FILE', '/home/j/jathan/sandbox/netdevices.json')
#NETDEVICES_FORMAT = 'json' # One of 'xml', 'json', 'sqlite'
#NETDEVICES_FILE = os.environ.get('NETDEVICES_FILE', '/home/j/jathan/sandbox/nd.db')
#NETDEVICES_FORMAT = 'sqlite' # One of 'xml', 'json', 'sqlite'

# Valid owning teams (e.g. device.owningTeam) go here. These are examples and should be
# changed to match your environment.
VALID_OWNERS = (
    #'Data Center',
    #'Backbone Engineering',
    #'Enterprise Networking',
)

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
DATABASE_NAME = ''
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = '127.0.0.1'
DATABASE_PORT = 3306

#===============================
# ACL Management
#===============================
# FILTER names of ACLs that should be skipped or ignored by tools
# NOTE: These should be the names of the filters as they appear on devices. We
# want this to be mutable so it can be modified at runtime.
# TODO (jathan): Move this into Redis and maintain with 'acl' command?
IGNORED_ACLS = []

# FILE names ACLs that shall not be modified by tools
# NOTE: These should be the names of the files as they exist in FIREWALL_DIR.
# Trigger expects ACLs to be prefixed with 'acl.'.  These are examples and
# should be replaced.
NONMOD_ACLS  = []

# Mapping of real IP to external NAT. This is used by load_acl in the event
# that a TFTP or connection from a real IP fails or explicitly when passing the
# --no-vip flag.
# format: {local_ip: external_ip}
VIPS = {}

#===============================
# ACL Loading/Rate-Limiting
#===============================
# All of the following settings are currently only used in ``load_acl``.  If
# and when the load_acl functionality gets moved into the API, this might
# change.

# Any FILTER name (not filename) in this list will be skipped during automatic loads.
AUTOLOAD_BLACKLIST = []

# Assign blacklist to filter for backwards compatibility
AUTOLOAD_FILTER = AUTOLOAD_BLACKLIST

# Modify this if you want to create a list that if over the specified number of
# routers will be treated as bulk loads.
# TODO (jathan): Provide examples so that this has more context/meaning. The
# current implementation is kind of broken and doesn't scale for data centers
# with a large of number of devices.
# Format:
# { 'filter_name': threshold_count }
AUTOLOAD_FILTER_THRESH = {}

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
#
# Format:
# { 'filter_name': max_hits }
BULK_MAX_HITS = {}

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
#
# If you don't want to return this information, have it return None.
GET_CURRENT_ONCALL = lambda x=None: x

#===============================
# CM Ticket Creation
#===============================
# This should be a function that creates a CM ticket and returns the ticket
# number, or None.
# TODO (jathan): Improve this interface so that it is more intuitive.
def _create_cm_ticket_stub(**args):
    return None

# If you don't want to use this feature, just have the function return None.
CREATE_CM_TICKET = _create_cm_ticket_stub
