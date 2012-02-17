.. _configuration:

============================
 Configuration and defaults
============================

This document describes the configuration options available.

If you're using the default loader, you must create or copy the
:file:`trigger_settings.py` module and make sure it is in ``/etc`` on the local
system.

.. contents::
    :local:
    :depth: 2

Configuration Directives
========================

Global settings
---------------

PREFIX
~~~~~~

This is where Trigger should look for its essential files including
:file:`autoacl.py` and :file:`netdevices.xml``. 

Default:: 

    '/usr/local/trigger'

USE_GPG_AUTH
~~~~~~~~~~~~

Toggles whether or not we should use GPG authentication for storing TACACS
credentials in the user's ``.tacacsrc`` file. Set to ``False`` to use the old
.tackf two-way hashing method, which sucks but requires almost no overhead.
Should be ``False`` unless instructions/integration is ready for GPG. At this
time the documentation for the GPG support is incomplete.

Default::

   False

TACACSRC_KEYFILE
~~~~~~~~~~~~~~~~

Only used if GPG auth is disabled. This is the location of the file that
contains the passphrase used for the two-way hashing of the user credentials
within the ``.tacacsrc`` file.

Default:: 

    '/usr/local/trigger/.tackf'

FIREWALL_DIR
~~~~~~~~~~~~

Location of firewall policy files.

Default::

    '/data/firewalls'

TFTPROOT_DIR
~~~~~~~~~~~~

Location of the tftproot directory.

Default:: 

    '/data/tftproot'

INTERNAL_NETWORKS
~~~~~~~~~~~~~~~~~

A list of ``IPy.IP`` objects describing your internally owned networks. All
network blocsk owned/operated and considered a part of your network should be
included. The defaults are private IPv4 networks defined by RFC 1918.

Default::

  [IPy.IP("10.0.0.0/8"), IPy.IP("172.16.0.0/12"), IPy.IP("192.168.0.0/16")]

SUCCESS_EMAILS
~~~~~~~~~~~~~~

A list of email addresses to email when things go well (such as from ``load_acl
--auto``). 
 
Default::

    []

FAILURE_EMAILS
~~~~~~~~~~~~~~

A list of email addresses to email when things go not well.

Default::

    []

Twister settings
----------------

These settings are used to customize the timeouts and methods used by Trigger
to connect to network devices.

DEFAULT_TIMEOUT
~~~~~~~~~~~~~~~

Default timeout in seconds for commands executed during a session. If a
response is not received within this window, the connection is terminated.

Default::

    300

TELNET_TIMEOUT
~~~~~~~~~~~~~~

Default timeout in seconds for initial telnet connections. 

Default::

    60

SSH_TYPES
~~~~~~~~~

A list of manufacturers that support SSH logins. Only add one if ALL devices of that 
# manufacturer have SSH logins enabled. (Don't forget the trailing comma when you add a new entry.)

Default:: 

    ['ARISTA NETWORKS', 'CITRIX', 'JUNIPER', 'NETSCREEN TECHNOLOGIES']

VALID_VENDORS
~~~~~~~~~~~~~

A tuple of strings containing the names of valid manufacturer names. These are
currently defaulted to what Trigger supports internally. Do not modify this
unless you know what you're doing!

Default:: 

    ('ARISTA NETWORKS', 'CISCO SYSTEMS', 'DELL', 'JUNIPER', 'FOUNDRY', 'CITRIX', 'BROCADE')

IOSLIKE_VENDORS
~~~~~~~~~~~~~~~

A tuple of strings containing the names of vendors that basically just emulate
Cisco's IOS and can be treated accordingly for the sake of interaction.

Default::

    ('ARISTA NETWORKS', 'BROCADE' 'CISCO SYSTEMS', 'DELL', 'FOUNDRY')

NetDevices settings
-------------------

VALID_OWNERS
~~~~~~~~~~~~

A tuple of strings containing the names of valid owning teams for
:class:`~trigger.netdevices.NetDevice` objects.. This is intended to be a
master list of the valid owners, to have a central configuration entry to
easily reference. The default value is an example and should be changed to
match your environment.

Default:: 

    ('Data Center', 'Backbone Engineering', 'Enterprise Networking')

Redis settings
--------------

REDIS_HOST
~~~~~~~~~~

Redis master server. This will be used unless it is unreachable.

Default::

    '127.0.0.1'

REDIS_PORT
~~~~~~~~~~

The Redis port.

Default::

    6379

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

These are all self-explanatory, I hope, and do not have default values.

DATABASE_NAME
~~~~~~~~~~~~~

The name of the database.

DATABASE_USER
~~~~~~~~~~~~~

The username to use to connect to the database.

DATABASE_PASSWORD
~~~~~~~~~~~~~~~~~

The password for the user account used to connect to the database.

DATABASE_HOST
~~~~~~~~~~~~~

The host on which your MySQL databse resides.

Default::

    '127.0.0.1'

DATABASE_PORT
~~~~~~~~~~~~~

The destination port used by MySQL.

Default::

    3306

Access-list Management settings
-------------------------------

These are various settings that control what files may be modified, by various
tools and libraries within the Trigger suite. These settings are specific to
the functionality found within the :module:`~trigger.acl` module.

IGNORED_ACLS
~~~~~~~~~~~~

This is a list of FILTER names of ACLs that should be skipped or ignored by
tools. These should be the names of the filters as they appear on devices. We
want this to be mutable so it can be modified at runtime.

Default::

    []

NONMOD_ACLS
~~~~~~~~~~~

This is a list of FILE names of ACLs that shall not be modified by tools. These
should be the names of the files as they exist in ``FIREWALL_DIR``. Trigger
expects ACLs to be prefixed with ``'acl.'``.  

Default::

    []

VIPS
~~~~

This is a dictionary mapping of real IP to external NAT IP address for used by your connecting host(s) (aka jump host). This is used primarily by ``load_acl`` in the event that a connection from a real IP fails (such as via tftp) or when explicitly passing the ``--no-vip`` flag. Format: ``{local_ip: external_ip}``

Default::

    {}

Access-list loading & rate-limiting settings
--------------------------------------------

All of the following esttings are currently only used by ``load_acl``. If and when the ``load_acl`` functionality gets moved into the library API, this may change.

AUTOLOAD_FILTER
~~~~~~~~~~~~~~~

A list of FILTER names (not filenames) that will be skipped during automated loads (``load_acl --auto``).  This setting was renamed from ``AUTOLOAD_BLACKLIST``; usage of that name is being phased out.

Default::

    []

AUTOLOAD_FILTER_THRESH
~~~~~~~~~~~~~~~~~~~~~~

A dictionary mapping for FILTER names (not filenames) and a numeric threshold. Modify this if you want to create a list that if over the specified number of devices will be treated as bulk loads.

For now, we provided examples so that this has more context/meaning. The current implementation is kind of broken and doesn't scale for data centers with a large of number of devices.

Default::

    {}

AUTOLOAD_BULK_THRESH
~~~~~~~~~~~~~~~~~~~~

Any ACL applied on a number of devices >= this number will be treated as bulk loads. For example, if this is set to 5, any ACL applied to 5 or more devices will be considered a bulk ACL load.

Default::

    10

BULK_MAX_HITS
~~~~~~~~~~~~~

This is a dictionary mapping of filter names to the number of bulk hits. Use this to override ``BULK_MAX_HITS_DEFAULT``. Please note that this number is used PER EXECUTION of ``load_acl --auto``. For example if you ran it once per hour, and your bounce window were 3 hours, this number should be the total number of expected devices per ACL within that allotted bounce window. Yes this is confusing and needs to be redesigned.)

Examples:
+ 1 per load_acl execution; ~3 per day, per 3-hour bounce window
+ 2 per load_acl execution; ~6 per day, per 3-hour bounce window

Default:


BULK_MAX_HITS_DEFAULT
~~~~~~~~~~~~~~~~~~~~~

If an ACL is bulk but not defined in ``BULK_MAX_HITS``, use this number as max_hits. For example using the default value of 1, that means load on one device per ACL, per data center or site location, per ``load_acl --auto`` execution.

Default::

    1

On-Call Engineer Display settings
---------------------------------

GET_CURRENT_ONCALL
~~~~~~~~~~~~~~~~~~

This variable should reference a function that returns data for your on-call engineer, or
failing that ``None``. The function should return a dictionary that looks like
this::

    {
        'username': 'mrengineer', 
        'name': 'Joe Engineer', 
        'email': 'joe.engineer@example.notreal'
    }

Default::

    lambda x=None: x

CM Ticket Creation settings
---------------------------

CREATE_CM_TICKET
~~~~~~~~~~~~~~~~

This variable should reference a function that creates a CM ticket and returns the ticket number, or ``None``. It defaults to ``_create_cm_ticket_stub``, which can be found within the trigger_settings.py source code and is a simple function that takes any arguments and returns ``None``.

Default::

    _create_cm_ticket_stub
