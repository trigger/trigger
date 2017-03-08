# Default Trigger settings. Override these with settings in the module
# pointed-to by the TRIGGER_SETTINGS environment variable. This is pretty much
# an exact duplication of how Django does this.

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
USER_HOME = os.getenv('HOME')
TACACSRC = os.getenv('TACACSRC', os.path.join(USER_HOME, '.tacacsrc'))
TACACSRC_KEYFILE = os.getenv('TACACSRC_KEYFILE', os.path.join(PREFIX, '.tackf'))

# If set, use the TACACSRC_PASSPHRASE, otherwise default to TACACSRC_KEYFILE
TACACSRC_USE_PASSPHRASE = False

# Use this passphrase to encrypt credentials.CHANGE THIS IN YOUR FILE BEFORE
# USING THIS IN YOUR ENVIRONMENT.
TACACSRC_PASSPHRASE = ''

# Default login realm to store user credentials (username, password) for
# general use within the .tacacsrc
DEFAULT_REALM = 'aol'

# Default terminal type of xterm if TERM isn't set
TERM_TYPE = os.getenv('TERM', 'xterm')

# List of plugins allowed to be importd by Commando. Plugins should be listed as
# strings depicting the absolute paths.
#
# e.g. ['trigger.contrib.config_device', 'trigger.contrib.show_clock', 'bacon.cool_plugin']
#
# Currently config_device and execute_commands are automatically imported.
BUILTIN_PLUGINS = [
    'trigger.contrib.commando.plugins.config_device',
    'trigger.contrib.commando.plugins.show_clock',
    'trigger.contrib.commando.plugins.show_version'
]
COMMANDO_PLUGINS = BUILTIN_PLUGINS

# Location of firewall policies
FIREWALL_DIR = '/data/firewalls'

# Location of tftproot.
TFTPROOT_DIR = '/data/tftproot'
TFTP_HOST = ''

# Add internally owned networks here. All network blocks owned/operated and
# considered part of your network should be included.
INTERNAL_NETWORKS = [
    IPy.IP("10.0.0.0/8"),
    IPy.IP("172.16.0.0/12"),
    IPy.IP("192.168.0.0/16"),
]

# A dictionary keyed by manufacturer name containing a list of the device types
# for each that is officially supported by Trigger.
SUPPORTED_PLATFORMS = {
    'a10': ['SWITCH'],
    'arista': ['SWITCH'],                         # Your "Cloud" network vendor
    'aruba': ['SWITCH'],                          # Aruba Wi-Fi controllers
    'avocent': ['CONSOLE'],
    'brocade': ['ROUTER', 'SWITCH'],
    'cisco': ['ROUTER', 'SWITCH', 'FIREWALL'],
    'citrix': ['SWITCH'],                         # Assumed to be NetScalers
    'cumulus': ['SWITCH'],  # Any white-label hardware running Cumulus Linux
    'dell': ['SWITCH'],
    'f5': ['LOAD_BALANCER', 'SWITCH'],
    'force10': ['ROUTER', 'SWITCH'],
    'foundry': ['ROUTER', 'SWITCH'],
    'juniper': ['FIREWALL', 'ROUTER', 'SWITCH'],  # Any devices running Junos
    'mrv': ['CONSOLE', 'SWITCH'],
    'netscreen': ['FIREWALL'],                    # Pre-Juniper NetScreens
    'paloalto': ['FIREWALL'],
    'pica8': ['ROUTER', 'SWITCH'],
}

# List of supported vendor names derived from SUPPORTED_PLATFORMS
SUPPORTED_VENDORS = list(SUPPORTED_PLATFORMS)
VALID_VENDORS = SUPPORTED_VENDORS  # For backwards compatibility

# A mapping of manufacturer attribute values to canonical vendor name used by
# Trigger. These single-word, lowercased canonical names are used throughout
# Trigger.
#
# If your internal definition differs from the UPPERCASED ones specified below
# (which they probably do), customize them here.
VENDOR_MAP = {
    'A10 NETWORKS': 'a10',
    'ARISTA NETWORKS': 'arista',
    'ARUBA NETWORKS': 'aruba',
    'AVOCENT': 'avocent',
    'BROCADE': 'brocade',
    'CELESTICA': 'cumulus',
    'CISCO SYSTEMS': 'cisco',
    'CITRIX': 'citrix',
    'CUMULUS': 'cumulus',
    'DELL': 'dell',
    'F5 NETWORKS': 'f5',
    'FORCE10': 'force10',
    'FOUNDRY': 'foundry',
    'JUNIPER': 'juniper',
    'MRV': 'mrv',
    'NETSCREEN TECHNOLOGIES': 'netscreen',
    'PICA8': 'pica8',
}

# The tuple of support device types
SUPPORTED_TYPES = (
    'CONSOLE',
    'DWDM',
    'FIREWALL',
    'LOAD_BALANCER',
    'ROUTER',
    'SWITCH'
)

# A mapping of of vendor names to the default device type for each in the
# event that a device object is created and the deviceType attribute isn't set
# for some reason.
DEFAULT_TYPES = {
    'a10': 'SWITCH',
    'arista': 'SWITCH',
    'aruba': 'SWITCH',
    'avocent': 'CONSOLE',
    'brocade': 'SWITCH',
    'citrix': 'SWITCH',
    'cisco': 'ROUTER',
    'cumulus': 'SWITCH',
    'dell': 'SWITCH',
    'f5': 'LOAD_BALANCER',
    'force10': 'ROUTER',
    'foundry': 'SWITCH',
    'juniper': 'ROUTER',
    'mrv': 'CONSOLE',
    'netscreen': 'FIREWALL',
    'paloalto': 'FIREWALL',
    'pica8': 'SWITCH',
}

# When a vendor is not explicitly defined within `DEFAULT_TYPES`, fallback to
# this type.
FALLBACK_TYPE = 'ROUTER'

# When a manufacturer/vendor is not explicitly defined, fallback to to this
# value.
FALLBACK_MANUFACTURER = 'UNKNOWN'

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

# Default ports for SSH
SSH_PORT = 22

# Default port for Telnet
TELNET_PORT = 23

# The preferred order in which SSH authentication methods are tried.
SSH_AUTHENTICATION_ORDER = ['password', 'keyboard-interactive', 'publickey']

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
    'dell': ['SWITCH'],    # Dell SSH is just straight up broken
    'foundry': ['SWITCH'], # Old Foundry switches only do SSHv1
}

# Vendors that basically just emulate Cisco's IOS and can be treated
# accordingly for the sake of interaction.
IOSLIKE_VENDORS = (
    'a10',
    'arista',
    'aruba',
    'brocade',
    'cisco',
    'cumulus',
    'dell',
    'force10',
    'foundry',
)

# Commands executed on devices by default.
STARTUP_COMMANDS_DEFAULT = ['terminal length 0']

# Startup commands are executed upon login to setup the terminal session for
# automated execution. Typically these are just to disable pagination or other
# settings related to capturing output asynchronously. Each vendor is mapped by
# name. Vendor platforms with differing startup commands based on their device
# type are now mapped with an underscore separation (e.g. 'Cisco ASA' becomes
# 'cisco_asa'). The platform-specific lookups are still done in code for now.
STARTUP_COMMANDS_MAP = {
    'a10': STARTUP_COMMANDS_DEFAULT,
    'arista': STARTUP_COMMANDS_DEFAULT + ['terminal width 999'],
    'aruba': ['no paging'], # v6.2.x this is not necessary
    'brocade': ['skip-page-display'],
    'brocade_vdx': STARTUP_COMMANDS_DEFAULT,
    'cisco': STARTUP_COMMANDS_DEFAULT,
    'cisco_asa': ['terminal pager 0'],
    'citrix': ['set cli mode page off'],
    'cumulus': [],  # No startup commands for Cumulus by default!
    'dell': ['terminal datadump'],
    'f5': ['modify cli preference pager disabled'],
    'force10': STARTUP_COMMANDS_DEFAULT,
    'foundry': ['skip-page-display'],
    'juniper': ['set cli screen-length 0'],
    'mrv': ['no pause'],
    'netscreen': ['set console page 0'],
    'paloalto': ['set cli scripting-mode on', 'set cli pager off'],
}

# Prompts sent by devices that indicate the device is awaiting user
# confirmation when interacting with the device. If a continue prompt is
# detected, Trigger will temporarily set this value to the prompt and send
# along the next command (for example if you're expecting such a prompt and you
# want to send along "yes"). These should be as specific as possible because we
# want to make sure bad things don't happen.
CONTINUE_PROMPTS = [
    'continue?',
    'proceed?',
    '(y/n):',
    '[y/n]:',
    '[confirm]',
    '[yes/no]: ',
    'overwrite file [startup-config] ?[yes/press any key for no]....',
    'Destination filename [running-config]? ',
]

# The file path where .gorc is expected to be found.
GORC_FILE = '~/.gorc'

# The only root commands that are allowed to be executed when defined within
# ``~.gorc``. They will be filtered out by `~trigger.gorc.filter_commands()`.
GORC_ALLOWED_COMMANDS = (
    'cli',
    'enable',
    'exit',
    'get',
    'monitor',
    'ping',
    'quit',
    'set',
    'show',
    'start',
    'term',
    'terminal',
    'traceroute',
    'who',
    'whoami'
)

#===============================
# NetDevices
#===============================

# Globally toggle whether to load ACL associations from the Redis database. If
# you don't have Redis or aren't using Trigger to manage ACLs set this to
# False.
WITH_ACLS = False

# The default administrative status (production vs. non-production) of new
# devices.
DEFAULT_ADMIN_STATUS = 'PRODUCTION'

# Path to the explicit module file for autoacl.py so that we can still perform
# 'from trigger.acl.autoacl import autoacl' without modifying sys.path.
AUTOACL_FILE = os.environ.get('AUTOACL_FILE', os.path.join(PREFIX, 'autoacl.py'))

# A tuple of data loader classes, specified as strings. Optionally, a tuple can
# be used instead of a string. The first item in the tuple should be the
# Loader's module, subsequent items are passed to the Loader during
# initialization.
NETDEVICES_LOADERS = (
    'trigger.netdevices.loaders.filesystem.JSONLoader',
    'trigger.netdevices.loaders.filesystem.XMLLoader',
    'trigger.netdevices.loaders.filesystem.SQLiteLoader',
    'trigger.netdevices.loaders.filesystem.RancidLoader',
    'trigger.netdevices.loaders.filesystem.CSVLoader',
)

# A path or URL to netdevices device metadata source data, which is used to
# populate trigger.netdevices.NetDevices. For more information on this, see
# NETDEVICES_LOADERS.
NETDEVICES_SOURCE = os.environ.get(
    'NETDEVICES_SOURCE', os.path.join(PREFIX, 'netdevices.json')
)

# TextFSM Vendor Mappings. Override this if you have defined your own TextFSM
# templates.
TEXTFSM_VENDOR_MAPPINGS = {
    "cisco": [ "ios", "nxos" ],
    "arista": [ "eos" ]
}

# TextFSM Template Path. Commando will attempt to match a given show command
# with a template within this folder.
TEXTFSM_TEMPLATE_DIR = os.getenv(
    'TEXTFSM_TEMPLATE_DIR', os.path.join(PREFIX, 'vendor/ntc_templates')
)

# TextFSM Vendor Mappings. Override this if you have defined your own TextFSM templates.
TEXTFSM_VENDOR_MAPPINGS = {
        "cisco": [ "ios", "nxos" ],
        "arista": [ "eos" ]
        }

# TextFSM Template Path. Commando will attempt to match a given show command with a template within this folder.
TEXTFSM_TEMPLATE_DIR = os.getenv('TEXTFSM_TEMPLATE_DIR', os.path.join(PREFIX, 'vendor/ntc_templates'))

# Whether to treat the RANCID root as a normal instance, or as the root to
# multiple instances. This is only checked when using RANCID as a data source.
RANCID_RECURSE_SUBDIRS = os.environ.get('RANCID_RECURSE_SUBDIRS', False)

# Valid owning teams (e.g. device.owningTeam) go here. These are examples and
# should be changed to match your environment.
VALID_OWNERS = (
    #'Data Center',
    #'Backbone Engineering',
    #'Enterprise Networking',
)

# Fields and values defined here will dictate which Juniper devices receive a
# ``commit-configuration full`` when populating ``NetDevice.commit_commands`.
# The fields and values must match the objects exactly or it will fallback to
# ``commit-configuration``.
JUNIPER_FULL_COMMIT_FIELDS = {
    #'deviceType': 'SWITCH',
    #'make': 'EX4200',
}

#===============================
# Prompt Patterns
#===============================
# Specially-defined, per-vendor prompt patterns. If a vendor isn't defined here,
# try to use IOSLIKE_PROMPT_PAT or fallback to DEFAULT_PROMPT_PAT.
PROMPT_PATTERNS = {
    'aruba': r'\(\S+\)(?: \(\S+\))?\s?#$', # ArubaOS 6.1
    #'aruba': r'\S+(?: \(\S+\))?\s?#\s$', # ArubaOS 6.2
    'avocent': r'\S+[#\$]|->\s?$',
    'citrix': r'\sDone\n$',
    # This pattern is a regex "or" combination of the Cumulus bash login prompt
    # and IOSLIKE_PROMPT_PAT (for vtysh support)
    'cumulus': r'(?:\S+(\(config(-[a-z:1-9]+)?\))?[\r\s]*#[\s\b]*$)|(?:.*(?:\$|#)\s?$)',
    'f5': r'.*\(tmos\).*?#\s{1,2}\r?$',
    'juniper': r'(?:\S+\@)?\S+(?:\>|#)\s$',
    'mrv': r'\r\n?.*(?:\:\d{1})?\s\>\>?$',
    'netscreen': r'(\w+?:|)[\w().-]*\(?([\w.-])?\)?\s*->\s*$',
    'paloalto': r'\r\n\S+(?:\>|#)\s?$',
    'pica8': r'\S+(?:\>|#)\s?$',
}

# When a pattern is not explicitly defined for a vendor, this is what we'll try
# next (since most vendors are in fact IOS-like).
IOSLIKE_PROMPT_PAT = r'\S+(\(config(-[a-z:1-9]+)?\))?[\r\s]*#[\s\b]*$'
IOSLIKE_ENABLE_PAT = r'\S+(\(config(-[a-z:1-9]+)?\))?[\r\s]*>[\s\b]*$'

# Generic prompt to match most vendors. It assumes that you'll be greeted with
# a "#" prompt.
DEFAULT_PROMPT_PAT = r'\S+#\s?$'

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

# These are self-explanatory, I hope. Use the ``init_task_db`` to initialize
# your database after you've created it! :)
DATABASE_ENGINE = 'mysql'   # Choose 'postgresql', 'mysql', 'sqlite3'
DATABASE_NAME = ''          # Or path to database file if using sqlite3
DATABASE_USER = ''          # Not used with sqlite3
DATABASE_PASSWORD = ''      # Not used with sqlite3
DATABASE_HOST = ''          # Set to '' for localhost. Not used with sqlite3
DATABASE_PORT = ''          # Set to '' for default. Not used with sqlite3.

#===============================
# ACL Management
#===============================
# Whether to allow multi-line comments to be used in Juniper firewall filters.
# Defaults to False.
ALLOW_JUNIPER_MULTILINE_COMMENTS = False

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
#
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
# Stage ACL changes
#===============================
# This variable should be a function that returns the contents of the ACL
# files that are being pushed and the tftp location for all of them
#
# input
# list of file names, optional log file and boolean for sanitizing
#
# return
# (
#    [<list of string of file contents an each file to push>],
#    [<list of the path to files on the tftp server to push>],
#    [<list of files that failed to stage>]
# )
def _stage_acls(acls, log=None, sanitize_acl=False):
    """stage the new ACL files for load_acl"""

    import os, shutil
    from trigger.acl import parse as acl_parse
    from trigger.conf import settings

    acl_contents = []
    tftp_paths = []

    fails = []

    for acl in acls:
        nonce = os.urandom(8).encode('hex')
        acl_nonce = '%s.%s' % (acl, nonce)
        src_file = os.path.join(settings.FIREWALL_DIR, acl)
        dst_file = os.path.join(settings.TFTPROOT_DIR, acl_nonce)

        if not os.path.exists(dst_file):
            try:
                shutil.copyfile(src_file, dst_file)
            except Exception as err:
                fails.append("Unable to stage TFTP File %s" % str(acls))
                continue
            else:
                os.chmod(dst_file, 0644)

        with open(src_file, 'r') as src_acl:
            file_contents = src_acl.read()
        acl_contents.append(file_contents)

        tftp_paths.append(acl_nonce)

        # strip comments if brocade
        if (sanitize_acl):
            msg = 'Sanitizing ACL {0} as {1}'.format(src_file, dst_file)
            log.msg(msg)
            aclobj = acl_parse(file_contents)
            aclobj.strip_comments()
            output = '\n'.join(aclobj.output(replace=True)) + '\n'
            with open(dst_file, 'w') as dst_acl:
                dst_acl.write(output)

    return acl_contents, tftp_paths, fails

STAGE_ACLS = _stage_acls


#===============================
# Get the TFTP source
#===============================
def _get_tftp_source(dev=None, no_vip=True): #False): #True):
    """
    Determine the right TFTP source-address to use (public vs. private)
    based on ``settings.VIPS``, and return that address.

    :param dev:
        A `~trigger.netdevices.NetDevice` object
    """
    from trigger.conf import settings
    import socket

    host = socket.gethostbyname(socket.getfqdn())

    if no_vip:
        return host
    elif host not in settings.VIPS:
        return host

    return settings.VIPS[host]

GET_TFTP_SOURCE = _get_tftp_source

#===============================
# OnCall Engineer Display
#===============================
# This should be a callable that returns data for your on-call engineer, or
# failing that None.  The function should return a dictionary that looks like
# this:
#
# {'username': 'joegineer',
#  'name': 'Joe Engineer',
#  'email': 'joe.engineer@example.notreal'}
#
# If you want to disable it, just have it return a non-False value.
# If you want to use it and have it block, have it return a False value (such
# as None)
#
# This example is just providing a string that indicates that on-call lookup is
# disabled.
#
# Default: returns 'disabled'
def _get_current_oncall_stub(*args, **kwargs):
    return 'disabled'

GET_CURRENT_ONCALL = _get_current_oncall_stub

#===============================
# CM Ticket Creation
#===============================
# This should be a callable that creates a CM ticket and returns the ticket
# number.
#
# If you want to disable it, just have it return a non-False value.
# If you want to use it and have it block, have it return a False value (such
# as None)
#
# This example is just providing a string that indicates that CM ticket
# creation is disabled.
#
# Default: returns ' N/A (CM ticket creation is disabled)'
def _create_cm_ticket_stub(*args, **kwargs):
    return ' N/A (CM ticket creation is disabled)'

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
