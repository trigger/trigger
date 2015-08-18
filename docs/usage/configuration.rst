.. _configuration:

==========================
Configuration and defaults
==========================

This document describes the configuration options available for Trigger.

If you're using the default loader, you must create or copy the provided
:file:`trigger_settings.py` module and make sure it is in
``/etc/trigger/settings.py`` on the local system.

.. contents::
    :local:
    :depth: 2

A Word about Defaults
=====================

There are two Trigger components that rely on Python modules to be provided on
disk in ``/etc/trigger`` and these are:

* :mod:`trigger.acl.autoacl` at ``/etc/trigger/autoacl.py``
* :mod:`trigger.conf` at ``/etc/trigger/settings.py``
* :mod:`trigger.changemgmt.bounce` at ``/etc/trigger/bouncy.py``

If your custom configuration either cannot be found or fails to import, Trigger
will fallback to the defaults.

settings.py
-----------

Using a custom settings.py
~~~~~~~~~~~~~~~~~~~~~~~~~~

You may override the default location using the ``TRIGGER_SETTINGS``
environment variable.

For example, set this variable and fire up the Python interpreter::

    % export TRIGGER_SETTINGS=/home/jathan/sandbox/trigger/conf/trigger_settings.py
    % python
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import os
    >>> os.environ.get('TRIGGER_SETTINGS')
    '/home/j/jathan/sandbox/netops/trigger/conf/trigger_settings.py'
    >>> from trigger.conf import settings

Observe that it doesn't complain. You have loaded ``settings.py`` from a custom
location!

Using global defaults
~~~~~~~~~~~~~~~~~~~~~

If you don't want to specify your own ``settings.py``, it will warn you and
fallback to the defaults::

    >>> from trigger.conf import settings
    trigger/conf/__init__.py:114: RuntimeWarning: Module could not be imported from /etc/trigger/settings.py. Using default global settings.
      warnings.warn(str(err) + ' Using default global settings.', RuntimeWarning)

autoacl()
---------

The :mod:`trigger.netdevices` and :mod:`trigger.acl` modules require
:func:`~trigger.acl.autoacl.autoacl`.

Trigger wants to import the :func:`~trigger.acl.autoacl.autoacl` function from
either a module you specify or, failing that, the default location.

Using a custom autoacl()
~~~~~~~~~~~~~~~~~~~~~~~~

You may override the default location of the module containing the autoacl()
function using the ``AUTOACL_FILE`` environment variable just like how you
specified a custom location for ``settings.py``.

Using default autoacl()
~~~~~~~~~~~~~~~~~~~~~~~

Just as with ``settings.py``, the same goes for :func:`~trigger.acl.autoacl.autoacl`::

    >>> from trigger.acl.autoacl import autoacl
    trigger/acl/autoacl.py:44: RuntimeWarning: Function autoacl() could not be found in /etc/trigger/autoacl.py, using default!
      warnings.warn(msg, RuntimeWarning)

Keep in mind this :func:`~trigger.acl.autoacl.autoacl` has the expected
signature but does nothing with the arguments and only returns an empty set::

    >>> autoacl('foo')
    set([])

Configuration Directives
========================

Global settings
---------------

.. setting:: PREFIX

PREFIX
~~~~~~

This is where Trigger should look for its essential files including
:file:`autoacl.py` and :file:`netdevices.xml`.

Default::

    '/etc/trigger'

.. setting:: USE_GPG_AUTH

USE_GPG_AUTH
~~~~~~~~~~~~

Toggles whether or not we should use GPG authentication for storing TACACS
credentials in the user's ``.tacacsrc`` file. Set to ``False`` to use the old
``.tackf`` encryption method, which sucks but requires almost no overhead.
Should be ``False`` unless instructions/integration is ready for GPG. At this
time the documentation for the GPG support is incomplete.

Default::

   False

.. setting:: TACACSRC

TACACSRC
~~~~~~~~

Sets the location of the ``.tacacsrc`` file.

You may override this by setting the ``TACACSRC`` environment variable to the
path of the file.

Default::

    '$HOME/.tacacsrc'

.. setting:: TACACSRC_KEYFILE

TACACSRC_KEYFILE
~~~~~~~~~~~~~~~~

Only used if GPG auth is disabled. This is the location of the file that
contains the passphrase used for the two-way hashing of the user credentials
within the ``.tacacsrc`` file.

You may override this by setting the ``TACACSRC_KEYFILE`` environment variable
to path of the file.

Default::

    '/etc/trigger/.tackf'

.. setting:: DEFAULT_REALM

DEFAULT_REALM
~~~~~~~~~~~~~

Default login realm to store user credentials (username, password) for general
use within the ``.tacacsrc`` file.

Default::

    'aol'

.. setting:: FIREWALL_DIR

FIREWALL_DIR
~~~~~~~~~~~~

Location of firewall policy files.

Default::

    '/data/firewalls'

.. setting:: TFTPROOT_DIR

TFTPROOT_DIR
~~~~~~~~~~~~

Location of the tftproot directory.

Default::

    '/data/tftproot'

.. setting:: INTERNAL_NETWORKS

INTERNAL_NETWORKS
~~~~~~~~~~~~~~~~~

A list of ``IPy.IP`` objects describing your internally owned networks. All
network blocsk owned/operated and considered a part of your network should be
included. The defaults are private IPv4 networks defined by RFC 1918.

Default::

  [IPy.IP("10.0.0.0/8"), IPy.IP("172.16.0.0/12"), IPy.IP("192.168.0.0/16")]

.. setting:: VENDOR_MAP

VENDOR_MAP
~~~~~~~~~~

.. versionadded:: 1.2

A mapping of manufacturer attribute values to canonical vendor name used by
Trigger. These single-word, lowercased canonical names are used throughout
Trigger.

If your internal definition differs from the UPPERCASED ones specified below
(which they probably do, customize them here.

Default::

    {
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

.. setting:: SUPPORTED_PLATFORMS

SUPPORTED_PLATFORMS
~~~~~~~~~~~~~~~~~~~

.. versionadded:: 1.2

A dictionary keyed by manufacturer name containing a list of the device types
for each that is officially supported by Trigger. Do not modify this unless you
know what you’re doing!

Default::

    {
        'a10': ['SWITCH'],
        'arista': ['SWITCH'],
        'brocade': ['ROUTER', 'SWITCH'],
        'cisco': ['ROUTER', 'SWITCH'],
        'citrix': ['SWITCH'],
        'dell': ['SWITCH'],
        'foundry': ['ROUTER', 'SWITCH'],
        'juniper': ['FIREWALL', 'ROUTER', 'SWITCH'],
        'netscreen': ['FIREWALL']
    }

.. setting:: SUPPORTED_VENDORS

SUPPORTED_VENDORS
~~~~~~~~~~~~~~~~~

A tuple of strings containing the names of valid manufacturer names. These are
currently defaulted to what Trigger supports internally. Do not modify this
unless you know what you're doing!

Default::

    ('a10', 'arista', 'brocade', 'cisco', 'citrix', 'dell', 'foundry',
    'juniper', 'netscreen')

.. setting:: SUPPORTED_TYPES

SUPPORTED_TYPES
~~~~~~~~~~~~~~~

A tuple of device types officially supported by Trigger. Do not modify this
unless you know what you’re doing!

Default::

    ('FIREWALL', 'ROUTER', 'SWITCH')

.. setting:: DEFAULT_TYPES

DEFAULT_TYPES
~~~~~~~~~~~~~

.. versionadded:: 1.2

A mapping of of vendor names to the default device type for each in the event
that a device object is created and the ``deviceType`` attribute isn't set for
some reason.

Default::

    {
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

.. setting:: FALLBACK_TYPE

FALLBACK_TYPE
~~~~~~~~~~~~~

.. versionadded:: 1.2

When a vendor is not explicitly defined within :setting:`DEFAULT_TYPES`, fallback to this type.

Default::

    'ROUTER'

Twister settings
----------------

These settings are used to customize the timeouts and methods used by Trigger
to connect to network devices.

.. setting:: DEFAULT_TIMEOUT

DEFAULT_TIMEOUT
~~~~~~~~~~~~~~~

Default timeout in seconds for commands executed during a session. If a
response is not received within this window, the connection is terminated.

Default::

    300

.. setting:: TELNET_TIMEOUT

TELNET_TIMEOUT
~~~~~~~~~~~~~~

Default timeout in seconds for initial telnet connections.

Default::

    60

.. setting:: TELNET_ENABLED

TELNET_ENABLED
~~~~~~~~~~~~~~

.. versionadded:: 1.2

Whether or not to allow telnet fallback. Set to ``False`` to disable support
for telnet.

Default::

    True

.. setting:: SSH_PORT

SSH_PORT
~~~~~~~~

.. versionadded:: 1.4.4

Destination TCP port to use for SSH client connections.

Default::

    22

.. setting:: SSH_AUTHENTICATION_ORDER

SSH_AUTHENTICATION_ORDER
~~~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 1.5.1

The preferred order in which SSH authentication methods are tried. Customize
this if you wish to change the order of, or modify the supported methods.

Default::

    ['password', 'keyboard-interactive', 'publickey']

.. setting:: TELNET_PORT

TELNET_PORT
~~~~~~~~~~~

.. versionadded:: 1.4.4

Destination TCP port to use for Telnet client connections.

Default::

    23

.. setting:: TRIGGER_ENABLEPW

TRIGGER_ENABLEPW
~~~~~~~~~~~~~~~~

.. versionadded:: 1.4.3

When connecting to devices that require the entry of an enable password (such
as when a ">" prompt is detected), Trigger may automatically execute the
"enable" command and pass the enable password along for you.

You may provide the enable password by setting the ``TRIGGER_ENABLEPW``
environment variable.

Default::

    None

.. setting:: SSH_PTY_DISABLED

SSH_PTY_DISABLED
~~~~~~~~~~~~~~~~

.. versionadded:: 1.2

A mapping of vendors to the types of devices for that vendor for which you
would like to disable interactive (pty) SSH sessions, such as when using
``bin/gong``.

Default::

    {
        'dell': ['SWITCH'],
    }

.. setting:: SSH_ASYNC_DISABLED

SSH_ASYNC_DISABLED
~~~~~~~~~~~~~~~~~~

.. versionadded:: 1.2

A mapping of vendors to the types of devices for that vendor for which you
would like to disable asynchronous (NON-interactive) SSH sessions, such as when using
`~trigger.twister.execute` or `~trigger.cmds.Commando` to remotely control a
device.

Default::

    {
        'arista': ['SWITCH'],
        'brocade': ['SWITCH'],
        'dell': ['SWITCH'],
    }

.. setting:: IOSLIKE_VENDORS

IOSLIKE_VENDORS
~~~~~~~~~~~~~~~

A tuple of strings containing the names of vendors that basically just emulate
Cisco's IOS and can be treated accordingly for the sake of interaction.

Default::

    ('a10', 'arista', 'brocade', 'cisco', 'dell', 'foundry')

.. setting:: CONTINUE_PROMPTS

CONTINUE_PROMPTS
~~~~~~~~~~~~~~~~

A list of strings representing continue prompts sent by devices that indicate
the device is awaiting user confirmation when interacting with the device. If a
continue prompt is detected, Trigger will temporarily set this value to the
prompt and send along the next command (for example if you're expecting such a
prompt and you want to send along "yes").

When checking these prompts, the incoming output data from the device will be
tested whether it **ends with** one of these prompts. These should be as
specific as possible, including trailing spaces.

The default values are common continue prompts encountered throughout the
lifetime of the Trigger project's development, and is by no means
comprehensive. If you need to customize these prompts for your environment,
utilize this setting.

Default::

    [
        'continue?',
        'proceed?',
        '(y/n):',
        '[y/n]:',
        '[confirm]',
        '[yes/no]: ',
        'overwrite file [startup-config] ?[yes/press any key for no]....'
    ]

.. setting:: GORC_FILE

GORC_FILE
~~~~~~~~~

The file path where a user's ``.gorc`` is expected to be found.

Default::

    '~/.gorc'

.. setting:: GORC_ALLOWED_COMMANDS

GORC_ALLOWED_COMMANDS
~~~~~~~~~~~~~~~~~~~~~

The only root commands that are allowed to be executed when defined within a
users's ``~/.gorc`` file. Any root commands not  specified here will be
filtered out by `~trigger.gorc.filter_commands()`.

Default::

    '~/.gorc'

NetDevices settings
-------------------

.. setting:: WITH_ACLS

WITH_ACLS
~~~~~~~~~

Globally toggle whether to load ACL associations from the Redis database. If
you don't have Redis or aren't using Trigger to manage ACLs set this to
``False``.

.. note::
   If you are doing work that does not require ACL information setting this to
   ``False`` can speed things up. Several libraries that interact with devices
   also have a ``with_acls`` argument to toggle this at runtime.

Default::

    True

.. setting:: AUTOACL_FILE

AUTOACL_FILE
~~~~~~~~~~~~

Path to the explicit module file for autoacl.py so that we can still perform
``from trigger.acl.autoacl import autoacl`` without modifying ``sys.path``.

Default::

    '/etc/trigger/autoacl.py'

.. setting:: NETDEVICES_FORMAT

NETDEVICES_FORMAT
~~~~~~~~~~~~~~~~~

.. deprecated:: 1.3
   Replaced by the :setting:`NETDEVICES_LOADERS` plugin system. This variable
   is no longer used in Trigger 1.3 and will be ignored.

One of ``json``, ``rancid``, ``sqlite``, ``xml``. This MUST match the actual
format of :setting:`NETDEVICES_FILE` or it won't work for obvious reasons.

Please note that RANCID support is experimental. If you use it you must specify
the path to the RANCID directory.

You may override this location by setting the ``NETDEVICES_FORMAT`` environment
variable to the format of the file.

Default::

    'xml'

.. setting:: NETDEVICES_FILE

NETDEVICES_FILE
~~~~~~~~~~~~~~~

.. deprecated:: 1.3
   Replaced by :setting:`NETDEVICES_SOURCE`. If you are using Trigger 1.3 or
   later, please do not define this variable.

Path to netdevices device metadata source file, which is used to populate
`~trigger.netdevices.NetDevices`. This may be JSON, RANCID, a SQLite3 database,
or XML. You must set :setting:`NETDEVICES_FORMAT` to match the type of data.

Please note that RANCID support is experimental. If you use it you must specify
the path to the RANCID directory.

You may override this location by setting the ``NETDEVICES_FILE`` environment
variable to the path of the file.

Default::

    '/etc/trigger/netdevices.xml'

.. setting:: NETDEVICES_LOADERS

NETDEVICES_LOADERS
~~~~~~~~~~~~~~~~~~

.. versionadded:: 1.3

A tuple of data loader classes, specified as strings. Optionally, a tuple can
be used instead of a string. The first item in the tuple should be the Loader's
module, subsequent items are passed to the Loader during initialization.

Loaders should inherit from `~trigger.netdevices.loader.BaseLoader`. For now,
please see the source code for the pre-defined loader objects at
``trigger/netdevices/loaders/filesystem.py`` for examples.

Default::

    (
        'trigger.netdevices.loaders.filesystem.XMLLoader',
        'trigger.netdevices.loaders.filesystem.JSONLoader',
        'trigger.netdevices.loaders.filesystem.SQLiteLoader',
        'trigger.netdevices.loaders.filesystem.CSVLoader',
        'trigger.netdevices.loaders.filesystem.RancidLoader',
    )

.. setting:: NETDEVICES_SOURCE

NETDEVICES_SOURCE
~~~~~~~~~~~~~~~~~

.. versionadded:: 1.3

A path or URL to netdevices device metadata source data, which is used to
populate `~trigger.netdevices.NetDevices` with `~trigger.netdevices.NetDevice`
objects. For more information on this, see :setting:`NETDEVICES_LOADERS`.

This value may be as simple as an absolute path to a file on your local system,
or it may be a fully-fledge URL such as
``http://user:pass@myhost.com:8080/stuff?foo=bar#fragment-data``. This URL data
is parsed and passed onto a `~trigger.netdevices.loader.BaseLoader` subclass
for retrieving device metadata.

You may override this location by setting the ``NETDEVICES_SOURCE`` environment
variable to the path of the file.

Default::

    '/etc/trigger/netdevices.xml'

.. setting:: RANCID_RECURSE_SUBDIRS

RANCID_RECURSE_SUBDIRS
~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 1.2

When using `RANCID <http://www.shrubbery.net/rancid>`_ as a data source, toggle
whether to treat the RANCID root as a normal instance, or as the root to
multiple instances.

You may override this location by setting the ``RANCID_RECURSE_SUBDIRS``
environment variable to any ``True`` value.

Default::

    False

.. setting:: VALID_OWNERS

VALID_OWNERS
~~~~~~~~~~~~

A tuple of strings containing the names of valid owning teams for
:class:`~trigger.netdevices.NetDevice` objects. This is intended to be a master
list of the valid owners to have a central configuration entry to easily
reference. Please see the sample settings file for an example to use in your
environment.


Default::

    ()

.. setting:: JUNIPER_FULL_COMMIT_FIELDS

JUNIPER_FULL_COMMIT_FIELDS
~~~~~~~~~~~~~~~~~~~~~~~~~~

Fields and values defined here will dictate which Juniper devices receive a
``commit-configuration full`` when populating
`~trigger.netdevices.NetDevice.commit_commands`. The fields and values must
match the objects exactly or it will fallback to ``commit-configuration``.

Example::

    # Perform "commit full" on all Juniper EX4200 switches.
    JUNIPER_FULL_COMMIT_FIELDS = {
        'deviceType': 'SWITCH',
        'make': 'EX4200',
    }

Default ::

    {}

Bounce Window settings
----------------------

.. setting:: BOUNCE_FILE

BOUNCE_FILE
~~~~~~~~~~~

.. versionadded:: 1.3

The path of the explicit module file containing custom bounce window mappings.
This file is expected to define a ``bounce()`` function that takes a
`~trigger.netdevices.NetDevice` object as an argument and returns a
`~trigger.changemgmt.BounceWindow` object.

You may override the default location of the module containing the ``bounce()``
function by setting the ``BOUNCE_FILE`` environment variable to the path of the
file.

Default::

    '/etc/trigger/bounce.py'

.. setting:: BOUNCE_DEFAULT_TZ

BOUNCE_DEFAULT_TZ
~~~~~~~~~~~~~~~~~

.. versionadded:: 1.3

The name of the default timezone for bounce windows. `Olson zoneinfo names
<http://en.wikipedia.org/wiki/Tz_database#Names_of_time_zones>`_ are used for
this in the format of *Area/Location*. All `~trigger.changemgmt.BounceWindow`
objects are configured using "US/Eastern".

Default::

    'US/Eastern'

.. setting:: BOUNCE_DEFAULT_COLOR

BOUNCE_DEFAULT_COLOR
~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 1.3

The default fallback window color for bounce windows. Must be one of 'green',
'yellow', or 'red'.

:green:
    **Low Risk**. Minor impact on user or customer environments. Backing-out
    the change, if required, is easily accomplished. User notification is often
    unnecessary.

:yellow:
    **Medium Risk**. Potential exists for substantially impacting user or
    customer environments. Backing-out the change, if required, can be
    accomplished in a reasonable timeframe.

:red:
    **High Risk**. The highest potential impact on users or cutomers. Any
    non-standard add, move or change falls into this category. Backing-out of a
    high-risk change may be time-consuming or difficult.

Default::

    'red'

Redis settings
--------------

.. setting:: REDIS_HOST

REDIS_HOST
~~~~~~~~~~

Redis master server. This will be used unless it is unreachable.

Default::

    '127.0.0.1'

.. setting:: REDIS_PORT

REDIS_PORT
~~~~~~~~~~

The Redis port.

Default::

    6379

.. setting:: REDIS_DB

REDIS_DB
~~~~~~~~

The Redis DB to use.

Default::

    0

.. _db-settings:

Database settings
-----------------

These will eventually be replaced with another task queue solution (such as
Celery). For now, you'll need to populate this with information for your
database.

These are all self-explanatory, I hope. For more information on database
drivers that you may need, please see :ref:`db-drivers`.

.. setting:: DATABASE_ENGINE

DATABASE_ENGINE
~~~~~~~~~~~~~~~

The database driver you intend to use for the task queue. This can be one of
``postgresql``, ``mysql``, ``sqlite3``. For the purpose of backwards
compatibility this defaults to ``mysql``.

Default::

    'mysql'

.. setting:: DATABASE_NAME

DATABASE_NAME
~~~~~~~~~~~~~

The name of the database. If using ``sqlite3``, this is the path to the database file.

Default::

    ''

.. setting:: DATABASE_USER

DATABASE_USER
~~~~~~~~~~~~~

The username to use to connect to the database. (Not used with ``sqlite3``)

Default::

    ''

.. setting:: DATABASE_PASSWORD

DATABASE_PASSWORD
~~~~~~~~~~~~~~~~~

The password for the user account used to connect to the database. (Not used with ``sqlite``)

Default::

    ''

.. setting:: DATABASE_HOST

DATABASE_HOST
~~~~~~~~~~~~~

The host on which your database resides. Set to empty string for localhost.
(Not used with ``sqlite3``)

Default::

    ''

.. setting:: DATABASE_PORT

DATABASE_PORT
~~~~~~~~~~~~~

The destination port used by the task queue. Set to empty string for default.
(Not used with ``sqlite3``)

Default::

    ''

Access-list Management settings
-------------------------------

These are various settings that control what files may be modified, by various
tools and libraries within the Trigger suite. These settings are specific to
the functionality found within the :mod:`trigger.acl` module.

.. setting:: IGNORED_ACLS

IGNORED_ACLS
~~~~~~~~~~~~

This is a list of FILTER names of ACLs that should be skipped or ignored by
tools. These should be the names of the filters as they appear on devices. We
want this to be mutable so it can be modified at runtime.

Default::

    []

.. setting:: NONMOD_ACLS

NONMOD_ACLS
~~~~~~~~~~~

This is a list of FILE names of ACLs that shall not be modified by tools. These
should be the names of the files as they exist in ``FIREWALL_DIR``. Trigger
expects ACLs to be prefixed with ``'acl.'``.

Default::

    []

.. setting:: VIPS

VIPS
~~~~

This is a dictionary mapping of real IP to external NAT IP address for used by
your connecting host(s) (aka jump host). This is used primarily by ``load_acl``
in the event that a connection from a real IP fails (such as via tftp) or when
explicitly passing the ``--no-vip`` flag.

Format: ``{local_ip: external_ip}``

Default::

    {}

Access-list loading & rate-limiting settings
--------------------------------------------

All of the following esttings are currently only used by ``load_acl``. If and
when the ``load_acl`` functionality gets moved into the library API, this may
change.

.. setting:: ALLOW_JUNIPER_MULTILINE_COMMENTS

ALLOW_JUNIPER_MULTILINE_COMMENTS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Whether to allow multi-line comments to be used in Juniper firewall filters.
The default behavior is to result in a syntax error when a multi-line comment
is detected when parsing a firewall filter using the `~trigger.acl` library.

Default::

    False

.. setting:: AUTOLOAD_FILTER

AUTOLOAD_FILTER
~~~~~~~~~~~~~~~

A list of FILTER names (not filenames) that will be skipped during automated
loads (``load_acl --auto``).  This setting was renamed from
``AUTOLOAD_BLACKLIST``; usage of that name is being phased out.

Default::

    []

.. setting:: AUTOLOAD_FILTER_THRESH

AUTOLOAD_FILTER_THRESH
~~~~~~~~~~~~~~~~~~~~~~

A dictionary mapping for FILTER names (not filenames) and a numeric threshold.
Modify this if you want to create a list that if over the specified number of
devices will be treated as bulk loads.

For now, we provided examples so that this has more context/meaning. The
current implementation is kind of broken and doesn't scale for data centers
with a large of number of devices.

Default::

    {}

.. setting:: AUTOLOAD_BULK_THRESH

AUTOLOAD_BULK_THRESH
~~~~~~~~~~~~~~~~~~~~

Any ACL applied on a number of devices >= this number will be treated as bulk
loads. For example, if this is set to 5, any ACL applied to 5 or more devices
will be considered a bulk ACL load.

Default::

    10

.. setting:: BULK_MAX_HITS

BULK_MAX_HITS
~~~~~~~~~~~~~

This is a dictionary mapping of filter names to the number of bulk hits. Use
this to override :setting:`BULK_MAX_HITS_DEFAULT`. Please note that this number is
used PER EXECUTION of ``load_acl --auto``. For example if you ran it once per
hour, and your bounce window were 3 hours, this number should be the total
number of expected devices per ACL within that allotted bounce window. Yes this
is confusing and needs to be redesigned.)

Examples:

+ 1 per load_acl execution; ~3 per day, per 3-hour bounce window
+ 2 per load_acl execution; ~6 per day, per 3-hour bounce window

Format: ``{'filter_name': max_hits}``

Default::

    {}

.. setting:: BULK_MAX_HITS_DEFAULT

BULK_MAX_HITS_DEFAULT
~~~~~~~~~~~~~~~~~~~~~

If an ACL is bulk but not defined in :setting:`BULK_MAX_HITS`, use this number as
max_hits. For example using the default value of 1, that means load on one
device per ACL, per data center or site location, per ``load_acl --auto``
execution.

Default::

    1

.. setting:: GET_TFTP_SOURCE

GET_TFTP_SOURCE
~~~~~~~~~~~~~~~

A callable that you may define within ``settings.py``, that given a
`~trigger.netdevices.NetDevice` object as an argument, will determine the right
TFTP source-address to utilize.

This is specifically used within the ``bin/load_acl`` tool when connecting to
IOS-like (Cisco clone) devices to push ACL changes by telling the device from
where to pull the change over TFTP.

The callable you define must take 2 arguments: ``dev`` (a NetDevice object),
and ``no_vip`` (a Boolean), and must return a hostname or IP address that  for
example::

    def _my_tftp_getter(dev=None, no_vip=True):
        return '1.2.3.4'

.. note::
   For the default implementation, please see the source code in
   `~trigger.conf.global_settings`. This version's behavior is modified by
   :setting:`VIPS` to help decied whether to utilize a public or private IP,
   and return that address.

Default::

    trigger.conf.global_settings._get_tftp_source()

.. setting:: STAGE_ACLS

STAGE_ACLS
~~~~~~~~~~

A callable that you may define within ``settings.py`` that given a list of ACL
filenames will stage the files in the appropriate location for them to be
retrieved, for example, via TFTP from a remote device. This could do anything
you require as a staging step prior to executing ACL changes such as uploading
files to another system.

This is specifically used within the ``bin/load_acl`` tool when preparing ACLs
to be loaded onto devices.

The callable you define must take 3 arguments: ``acls`` (a list of filenames),
``log`` (a Twisted Python logging object), and ``sanitize_acls`` (a Boolean).
It must return a 3-tuple of (acl_contents, file_paths, failures), where:
``acl_contents`` is a list of strings where each string is the entire contents
of an ACL file, ``file_paths`` is a list of file paths used to locate the files
(such as for use with TFTP, and ``fails`` an error string indicating an failure
or ``None`` indicating success. For example::

    def _my_stage_acls(acls, log=None, sanitize_acls=False):
        acl_contents = []
        file_paths = []
        fails = None
        for acl in acls:
            if sanitize_acls:
                # Do stuff to the acl
            file_contents = open(acl).read()
            if not file_contents:
                fails = "%s could not be read"
                log.msg(fails)
                return ([], [], fails)
            acl_contents.append(file_contents)

        log.msg('All ACLs ready for staging')
        return (acl_contents, file_paths, fails)

.. note::
   For the default implementation, please see the source code in
   `~trigger.conf.global_settings`. This expects to find ACL files within
   :setting:`FIREWALL_DIR` and to stage them into :setting:`TFTPROOT_DIR`,
   which assumes that the TFTP server is running on the local system.

Default::

    trigger.conf.global_settings._stage_acls()

On-Call Engineer Display settings
---------------------------------

.. setting:: GET_CURRENT_ONCALL

GET_CURRENT_ONCALL
~~~~~~~~~~~~~~~~~~

This variable should reference a function that returns data for your on-call
engineer, or failing that ``None``. The function should return a dictionary
that looks like this::

    {
        'username': 'mrengineer',
        'name': 'Joe Engineer',
        'email': 'joe.engineer@example.notreal'
    }

Default::

    lambda x=None: x

CM Ticket Creation settings
---------------------------

.. setting:: CREATE_CM_TICKET

CREATE_CM_TICKET
~~~~~~~~~~~~~~~~

This variable should reference a function that creates a CM ticket and returns
the ticket number, or ``None``. It defaults to ``_create_cm_ticket_stub``,
which can be found within the ``settings.py`` source code and is a simple
function that takes any arguments and returns ``None``.

Default::

    _create_cm_ticket_stub

Notification settings
---------------------

.. setting:: EMAIL_SENDER

EMAIL_SENDER
~~~~~~~~~~~~

.. versionadded:: 1.2.2

The default email sender for email notifications. It's probably a good idea to
make this a no-reply address.

Default::

    'nobody@not.real'

.. setting:: SUCCESS_EMAILS

SUCCESS_EMAILS
~~~~~~~~~~~~~~

A list of email addresses to email when things go well (such as from ``load_acl
--auto``).

Default::

    []

.. setting:: FAILURE_EMAILS

FAILURE_EMAILS
~~~~~~~~~~~~~~

A list of email addresses to email when things go not well.

Default::

    []

.. setting:: NOTIFICATION_SENDER

NOTIFICATION_SENDER
~~~~~~~~~~~~~~~~~~~

.. versionadded:: 1.2.2

The default sender for integrated notifications. This defaults to the
fully-qualified domain name (FQDN) for the local host.

Default::

    socket.gethostname()

.. setting:: SUCCESS_RECIPIENTS

SUCCESS_RECIPIENTS
~~~~~~~~~~~~~~~~~~

.. versionadded:: 1.2.2

Destinations (hostnames, addresses) to notify when things go well.

Default::

    []

.. setting:: FAILURE_RECIPIENTS

FAILURE_RECIPIENTS
~~~~~~~~~~~~~~~~~~

.. versionadded:: 1.2.2

Destinations (hostnames, addresses) to notify when things go not well.

Default::

    []

.. setting:: NOTIFICATION_HANDLERS

NOTIFICATION_HANDLERS
~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 1.2.2

This is a list of fully-qualified import paths for event handler functions.
Each path should end with a callable that handles a notification event and
returns ``True`` in the event of a successful notification, or ``None``.

To activate a handler, add it to this list. Each handler is represented by a
string: the full Python path to the handler's function name.

Handlers are processed in order. Once an event is succesfully handled, all
processing stops so that each event is only handled once.

Until this documentation improves, for a good example of how to create a
custom handler, review the source code for
`~trigger.utils.notifications.handlers.email_handler()`.

Default::

    [
        'trigger.utils.notifications.handlers.email_handler',
    ]
