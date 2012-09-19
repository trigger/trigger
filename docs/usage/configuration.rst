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
.tackf encryptoin method, which sucks but requires almost no overhead.
Should be ``False`` unless instructions/integration is ready for GPG. At this
time the documentation for the GPG support is incomplete.

Default::

   False

.. setting:: TACACSRC_KEYFILE

TACACSRC_KEYFILE
~~~~~~~~~~~~~~~~

Only used if GPG auth is disabled. This is the location of the file that
contains the passphrase used for the two-way hashing of the user credentials
within the ``.tacacsrc`` file.

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

NetDevices settings
-------------------

.. setting:: AUTOACL_FILE

AUTOACL_FILE
~~~~~~~~~~~~

Path to the explicit module file for autoacl.py so that we can still perform ``from trigger.acl.autoacl import autoacl`` without modifying ``sys.path``.

Default::

    '/etc/trigger/autoacl.py'

.. setting:: NETDEVICES_FORMAT

NETDEVICES_FORMAT
~~~~~~~~~~~~~~~~~

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

Path to netdevices device metadata source file, which is used to populate
`~trigger.netdevices.NetDevices`. This may be JSON, RANCID, a SQLite3 database,
or XML. You must set :setting:`NETDEVICES_FORMAT` to match the type of data.

Please note that RANCID support is experimental. If you use it you must specify
the path to the RANCID directory.

You may override this location by setting the ``NETDEVICES_FILE`` environment
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

Database settings
-----------------

These will eventually be replaced with Redis or another task queue solution
(such as Celery). For now, you'll need to populate this with information for
your MySQL database.

These are all self-explanatory, I hope.

.. setting:: DATABASE_NAME

DATABASE_NAME
~~~~~~~~~~~~~

The name of the database.

Default::

    ''

.. setting:: DATABASE_USER

DATABASE_USER
~~~~~~~~~~~~~

The username to use to connect to the database.

Default::

    ''

.. setting:: DATABASE_PASSWORD

DATABASE_PASSWORD
~~~~~~~~~~~~~~~~~

The password for the user account used to connect to the database.

Default::

    ''

.. setting:: DATABASE_HOST

DATABASE_HOST
~~~~~~~~~~~~~

The host on which your MySQL databse resides.

Default::

    '127.0.0.1'

.. setting:: DATABASE_PORT

DATABASE_PORT
~~~~~~~~~~~~~

The destination port used by MySQL.

Default::

    3306

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
