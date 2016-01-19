=========
Changelog
=========

.. _v1.5.3:

1.5.3
=====

New Features
------------

+ Remote execution on Avocent console servers is now officially supported.
+ Example `normalizer
  <https://github.com/trigger/trigger/tree/develop/examples/normalizer>`_
  project added to the ``examples`` directory at the root of the repository.

Enhancements
------------

+ An identity test for `~trigger.netdevices.NetDevice` objects has been added
  that can be used to check whether a devices is a Cisco Nexus. You may utilize
  it by calling `.is_cisco_nexus()` on any `NetDevice` object.
+ Support for parsing interfaces on Cisco Nexus devices has been added.
+ A new global setting now defines what to do when a device object does not
  have a manufacturer defined (See: :setting:`FALLBACK_MANUFACTURER`) which
  defaults to the value ``UNKNOWN``.
+ :feature:`212` The `~trigger.twister` module is now PEP8-compliant.

Bug Fixes
---------

+ Fixed a bug where devices w/ mixed case names aren't properly detected by
  `~trigger.cmds.Commando` subclasses, since
  `~trigger.netdevices.NetDevices` normalizes the hostname on load.
+ :bug:`236` Fixed a bug in `~trigger.changemgmt` so that Trigger can use the
  current version of ``pytz``.
+ :bug:`238` Fixed a bug where sending an enable password to a device in a low
  latency environment (sub 1 ms) would result in the password being sent before
  the password prompt is displayed by the device.
+ :bug:`241` Pin Twisted version to 15.4.0 so that py2.6 unit tests succeed.
  (Twisted 15.5.0 dropped support for Python 2.6)

.. _v1.5.2:

1.5.2
=====

New Features
------------

+ `~trigger.netdevices.NetDevices` can now be properly subclassed and extended.
+ A disable paging command has been added for Citrix NetScaler devices.
+ String patterns used for detecting continue prompts is now globally
  configurable. (See :setting:`CONTINUE_PROMPTS`)

Bug Fixes
---------

+ :bug:`210` Addressed an issue where the buffer storing results from a command
  was not properly cleared when output continued to be sent after the prompt
  was displayed.
+ `bin/run_cmds` will now no longer hide errors when in `--verbose` mode.

.. _v1.5.1:

1.5.1
=====

New Features
------------

+ The SSH authentication order is now a configurable setting. Public key is now
  the last method by default, but this is now easily configured in
  ``settings.py`` using the new :setting:`SSH_AUTHENTICATION_ORDER` setting.
+ The ``command_interval`` argument may now be passed to
  `~trigger.cmds.Commando` and its subclasses. This allows you to specify a
  delay time in seconds to wait between sending commands to devices.

Enhancements
------------

+ The example script the Trigger XMLRPC service has been improved to check the
  pid file and kill the existing ``twistd`` process by process id.

.. _v.1.5:

1.5
===

.. warning::
   This release has introduced a change the ``Commando.parse()`` method that
   WILL require a minor change to any subclasses of Commando in your
   applications.

   You will need to modify any custom ``from_{vendor}`` methods to take an
   optional ``commands`` argument. It is recommended that you add
   ``commands=None``.

Bug Fixes
---------

+ :bug:`168` Fixed a bug in `~trigger.cmds.Commando.parse()` where `None` was listed as
  the command in results causing result data to be lost.

.. _v1.4.9:

1.4.9
=====

New Features
------------

+ Support for Pica8 routers and switches has been added!
+ :feature:`135` Support for SSH public key authentication has been added!
+ An ehancement to `~trigger.cmds.Commando.select_next_device()` to support
  skipping a `~trigger.netdevices.NetDevice` object for selection. If you
  overload this method in a subclass and want to skip the device, just return
  ``None``!

.. _v1.4.8:

1.4.8
=====

New Features
------------

+ Cisco ASA firewall now supported as a NetDevice. To begin using, ensure
  that ``FIREWALL`` is added in your settings.py as a supported cisco platform.o

  For it to enable properly, either the netdevice attribute ``enablePW`` needs
  to be set or the environment variable ``TRIGGER_ENABLEPW`` does. For now, I
  typically accomplish this via::

      >>> from trigger.conf import settings
      >>> from trigger import tacacsrc
      >>> settings.DEFAULT_REALM = 'MyRealm'
      >>> os.environ['TRIGGER_ENABLEPW'] = \
              tacacsrc.get_device_password(settings.DEFAULT_REALM).password
      >>> # Then the rest of my program

  ACL parsing for ASA is not implemented yet. NetACLInfo will generate the
  proper command, but will currently just add a message warning about future
  support


.. _v1.4.7:

1.4.7
=====

New Features
------------

+ The .tacacsrc passphrase may now be stored in ``settings.py``.

Bug Fixes
---------

+ :bug:`144` Bugfix to detect missing or empty .tacacsrc keyfile.

Bug Fixes
---------

.. _v1.4.6:

1.4.6
=====

Bug Fixes
---------

+ :bug:`198` Fix hanging SSH connections to Cisco equipment due to client
  sending key exchange messages before remote device.

.. _v1.4.5:

1.4.5
=====

New Features
------------

+ There is now a MongoDB loader for `~trigger.netdevices.NetDevices`.
+ :feature:`140` There is a new `~trigger.cmds.ReactorlessCommando` that allows
  for running multiple `~trigger.cmds.Commando` instances in the same program
  under the same reactor by preventing the instances from doing it themselves.
+ :feature:`182` ``bin/run_cmds`` will now log all activity to a logfile in ``/tmp``
+ :feature:`195` The `~trigger.acl` library has been refactored to be more
  modular, breaking out vendor-specific grammar details into their own modules
  (`~trigger.acl.ios`, `~trigger.acl.junos`).

Documentation
-------------

+ Improved the documentation for :doc:`usage/tacacsrc`.
+ The :doc:`installation` page now includes instructions for using
  ``bounce.py`` to configure maintenance windows.

Bug Fixes
---------

+ Make sure Juniper SRX devices are not categorized as being NetScreen devices
+ Bugfix in `~trigger.netdevices.NetDevice.is_netscreen()` to account for when
  ``.make`` is ``None``
+ Minor bugfix in ``start_xmlrpc.sh`` example script

.. _v1.4.4:

1.4.4
=====

Enhancements
------------

+ Client connectings (such as those made by ``bin/load_acl``, for example)
  will now raise an error when it is detected that an enable password is
  required and one is not provided.
+ :feature:`181` Added SSH support for confirmation prompts

  - Added ``'[confirm]'`` as one of those prompts

Bug Fixes
---------

+ :bug:`172` Added ability to specify remote port for NetDevice objects

  - Add defaults in settings.py for SSH (SSH_PORT) and Telnet (SSH_TELNET)
    ports
  - Added documentation for SSH_PORT and TELNET_PORT in settings.py

+ :bug:`180` Fix prompt patterns to include optional space and hard
  line-endings.
+ :bug:`184` Pin pytz<=2014.2 to fix unit tests for time being (no pun
  intended).
+ Fix a minor bug causing ``bin/gong`` send the enable password when it
  shouldn't.
+ Bugfix when passwords are passed in to make sure they are not unicode
+ ``bin/gong`` will now mark a device as enabled when auto-enable is detected.

.. _v1.4.3:

1.4.3
=====

New Features
------------

+ Added a new ``bin/check_syntax`` tool to determine if an ACL passes a
  syntax check.
+ Acceptance tests can now be run standalone from within a clone of the
  Trigger repo.
+ :feature:`142` ``bin/gong`` now enables on login if the enable
  password is provided by way of :setting:`TRIGGER_ENABLEPW`.

Enhancements
------------

+ Improvements to user-experience within ``bin/acl``

  - Help text greatly improved and expanded to be more helpful

    * ``-l`` and ``-m`` args now print a message when load queue is
      empty
    * Clarified help text for ``-a`` and ``-r`` args

  - It now requires users to explicitly ask for associations
    instead of it being default.
  - The wording on the status output has been improved for clarity
    and conciseness.

+ ``bin/load_acl`` will now validate ``.tacacsrc`` before work begins

Bug Fixes
---------

+ Bugfix in `~trigger.tacacs.Tacacsrc` in which saving a password
  longer than a certain length could cause the encrypted password hash
  to contain newlines and therefore become unreadable.
+ :bug:`163` Bugfix to copy startup commands from a device when creating
  a channel base, otherwise they will get consumed directly from the
  device, and connections after the first will not send any startup
  commands.
+ :bug:`157` Bugfix in which
  `~trigger.twister.TriggerTelnetClientFactory` was missing the
  ``device`` attribute.
+ Fix a bug causing a crash when using ``gnng --dotty``
+ Bugfix in `~trigger.twister.pty_connect()` to check for telnet
  fallback before attempting to telnet over pty that would cause a race
  condition resulting in a crash if neither telnet or SSH are available.
+ Catch invalid hostnames before they bleed through in stderr output
  when using `~trigger.utils.network.ping`
+ Bugfix to catch exceptions for bad netdevices data in ``bin/netdev``.
+ Fix bugs in auto-enable and remote execution on certain devices

  - The correct delimiter is now mapped out by vendor/platform and
    attached to the NetDevice object at runtime.
  - Fixed a bug when executing commands remotely on NetScreen
    devices running ScreenOS that was causing them to be treated
    as Juniper routers/switches if the NetDevice attributes
    vendor=juniper and deviceType=netscreen.

+ :bug:`151` Gong now uses chosen dev. from multiple when updating
  ``.tacacsrc``.
+ :bug:`90` Bugfix causing
  `~trigger.netdevices.loaders.filesystem.CSVLoader` for netdevices to
  always succeed.

.. _v1.4.2:

1.4.2
=====

Warnings
--------

+ With this update, load_acl and acl no longer assume ACL and filter files
  begin with 'acl.'.  There are two options for updating your deployment to
  work with this code:

  1. Move files in settings.FIREWALL_DIR to files without the prepended 'acl.'.
  2. Update autoacls.py and explicit ACL associations to include the prepended
     'acl.'  prepend_acl_dot was included in tools/ to help update explicit ACL
     associations.

+ Please note that either change above may have an impact on any non-trigger code.

New Features
------------

+ ACL staging and finding tftp server moved to global settings

  - Allows for more site specific configuration

+ Load_acl support for new vendors

  - Force10

+ Enhancements to various ACL-related CLI tools
+ Moved staging and tftp server definitions to global settings
  to allow for site specific configuratons
+ Added tftpy package to trigger.packages.tftpy (MIT License)


Bug Fixes
---------

+ Helpful netdev output when no devices found from search
+ :bug:`100` Bug fix to add acl parser support for then accept;
+ :bug:`132` Bugfix to handle inactive IP addresses in acl parser
+ :bug:`133` Bugfix to added interface-specific support for Juniper filters

.. _v1.4.1:

1.4.1
=====

New Features
------------

+ Support for new vendors and platforms!!

  - F5 BIG-IP application delivery controllers and server load-balancers
  - MRV LX-series console servers

+ New tool ``bin/run_cmds`` to run commands from the CLI!

Documentation Enhancements
--------------------------

+ API documentation fixes for trigger.contrib and some logging
  fixes

Bug Fixes
---------

+ :bug:`97` Bugfix that was causing NameError crash in
  ``bin/optimizer``.
+ :bug:`124` Bugfix in `~trigger.utils.cli.pretty_time` where
  global timezone was hard-coded.
+ :bug:`127` Bugfix to handle SSH protocol errors as if they are
  login failures instead of exiting with a cryptic error.
+ Bugfix in Tacacsrc when updating credentials for a user.
+ Tacacsrc will now truly enforce file permissions on the
  .tacacsrc when reading or writing the file

.. _v1.4:

1.4
===

Trigger has a new home at `https://github.com/trigger/trigger
<https://github.com/trigger/trigger>`_!

New Features
------------

+ Support for new vendors and platforms!!

  - Aruba wireless controllers
  - Cisco Nexus switches running NX-OS
  - Force10 routers and switches

+ Trigger now has a `~trigger.contrib` package for optional extensions
  to core Trigger features.

  - A pluggable XMLRPC `~trigger.contrib.xmlrpc.server` that can be
    used as a long-running event loop.
  - Plugins for use w/ the XMLRPC server

+ Task `~trigger.acl.queue` now supports MySQL, PostgreSQL, or SQLite.
  See the :ref:`db-settings` for more information!

  - There's a new :setting:`DATABASE_ENGINE` that allows you to specify.
  - New tool to initialize your database w/ ease: ``init_task_db``

+ All legacy unit tests have been fixed and Trigger is now fully
  integrated with `Travis CI <http://traviw-ci.org>`_. All new
  functionality will be fully tested, and the existing unit testing
  suite will be continually improved.
+ You may now globally disable ACL support by toggling
  :setting:`WITH_ACLS` in ``settings.py``.

  - All `~trigger.twister.execute()` methods and `~trigger.cmds.Commando`
    objects now support a ``with_acls`` argument to toggle this at runtime.
  - We also turned off ACLs for scripts that will never use them.

+ All `~trigger.twister.execute()` methods and `~trigger.cmds.Commando` objects
  now support a ``force_cli`` argument to force commands to be sent as CLI
  commands and return human-readable output instead of structured output.
  Currently this is only relevant for Juniper devices, which return XML by
  default.

+ :feature:`54` Commands allowed in ``.gorc`` can now be customized in
  ``settings.py`` (See :setting:`GORC_ALLOWED_COMMANDS` for more
  information)
+ Vastly expanded debug logging to include device hostname whenever
  possible. (You're welcome!)

Bug fixes
---------

+ Fix AttributeError when trying to connect interactively causing
  logins to fail.
+ :bug:`74` - Bugfix in error-detection for NetScaler devices
+ Bugfix in host lookup bug in `~trigger.twister.TriggerTelnet`
  causing telnet channels to crash.
+ Fix typo that was causing Cisco ACL parsing to generate an unhandled
  exception.
+ Fix typos in ``tools/tacacsrc2gpg.py`` that were causing it to
  crash.
+ :bug:`119` - Get custom importlib from trigger.utils vs. native (for
  supporting Python < 2.6).
+ Replace all calls to ``os.getlogin()`` causing "Invalid argument"
  during unit tests where the value ``$USER`` is not set.
+ Various bugfixes and improvements to the handling of async SSH
  execution.
+ :bug:`33` Console paging is now disabled by default for SSH
  Channels.
+ :bug:`49` Bugfix in ACL `~trigger.acl.parser` to omit src/dst ports if
  range is 0-65535.
+ Bugfix in ACL parser showing useless error when address fails to parse
+ Bugfix in `~trigger.acl.RangeList` objects causing numeric
  collapsing/expanding to fail
+ Bugfix in `~trigger.cmds.Commando` causing results from multiple Commando
  instances to collide with each other because they were inheriting an empty
  dictionary from the class object.

CLI Tools
---------

+ ``bin/gnng`` - Added flags to include un-numbered (-u) or disabled (-d)
  interfaces.

trigger.acl
-----------

+ Minimal changes to support writing Dell ACLs
+ Parser modifications to support negation of address objects in Junos
  ACLs. (Note that this relies on marking up ACLs with 'trigger: make
  discard' in term comments. This is undocmented functionality,
  currently used internally within AOL, and this code will only be
  used for Junos output.)
+ :feature:`47` Add parsing of ranges for ``fragment-offset`` in Juniper ACLs

trigger.changemgmt
------------------

+ Refactored `~trigger.changemgt.BounceWindow` definition syntax to be
  truly usable by humans.

trigger.cmds
------------

+ `~trigger.cmds.NetACLInfo` and ``bin/gnng`` can now include disabled
  or un-addressed interfaces in their results.
+ Added ``pyparsing`` as a hard requirement until further notice so that
  `~trigger.cmds.NetACLInfo` and ``bin/gnng`` will behave as expected
  without confusing developers and users alike.
+ You may now pass login credentials to `~trigger.cmds.Commando` using the
  ``creds`` argument.

trigger.netdevices
------------------

+ Prompt patterns are now bound to `~trigger.netdevices.Vendor`
  objects.

trigger.tacacsrc
----------------

+ Added a utility function `~trigger.tacacsrc.validate_credentials()` to ...
  validate credentials ... and return a `~trigger.tacacsrc.Credentials` object.

trigger.twister
---------------

+ The new default operating mode for SSH channels is to use shell +
  pty emulation.
+ :feature:`56` You may now optionally run "commit full" on Juniper
  devices. (See :setting:`JUNIPER_FULL_COMMIT_FIELDS` for more
  information)
+ Added support for sending an enable password to IOS-like devices
  when an enable prompt is detected.

  - This can either be provided in your netdevices metadata by
    populating the ``enablePW`` attribute, or by setting the
    environment variable ``TRIGGER_ENABLEPW`` to the value of the
    enable password.

+ Added error-detection for Brocade MLX routers.
+ `~trigger.tacacsrc.Tacacrc()` is now only called once when creds aren't
  provided upon creation of new clients.

trigger.utils
-------------

+ New utility module `~trigger.utils.xmltodict` for convert XML into
  dictionaries, primarily so such objects can be serialized into JSON.

.. _v1.3.1:

1.3.1
=====

+ General changes

  - New contrib package for optional extensions to core Trigger
    features, `~trigger.contrib.commando.CommandoApplication` being
    the first.
  - Remove legacy mtsync check from bin/fe.
  - Conditionally import MySQLdb so we can still do testing without
    it.

+ The following changes have been madw within `~trigger.acl.parser`,
  which provides Trigger's support for parsing network access control
  lists (ACLs) and firewall policies:

  - :bug:`72` Bugfix in `~trigger.acl.parser.TIP` where an invalid
    network preifx (e.g. '1.2.3.1/31' would throw an
    ``AttributeError`` when checking the ``negated`` attribute and
    shadowing the original ``ValueError``.

+ The following changes have been made within `~trigger.cmds`, which
  provides an extensible, developer-friendly interface to writing
  command exeuction adapters:

  - Added ``with_errors`` argument to `~trigger.cmds.Commando`
    constructor to toggle whether errors are raised as exceptions or
    returned as strings.
  - Allow timeout to be set as a class variable in
    `~trigger.cmds.Commando` subclasses, preferrring timeout passed to
    constructor in `~trigger.cmds.Commando` subclasses.

+  The following changes have been made within `~trigger.netdevices`:

  - Refactor how we id Brocade switches for startup/commit (fix #75)

    * It's assumed that all Brocade devices all act the same;
    * Except in the case of the VDX, which is treated specially.

  - Simplified how ``startup_commands`` are calculated
  - Disable SQLite loader if sqlite3 isn't available for some reason.
  - Prompt patterns are now bound to `~trigger.netdevices.Vendor`
    objects object when `~trigger.netdevices.NetDevices` is populated.
  - `~trigger.netdevices.Vendor` objects now have a ``prompt_pattern``
    attribute.
  - All prompt patterns are now defined in ``settings.py``:

    * Vendor-specific: :setting:`PROMPT_PATTERNS`
    * IOS-like: :setting:`IOSLIKE_PROMPT_PAT`
    * Fallback: :setting:`DEFAULT_PROMPT_PAT`

+ The following changes have been made within `~trigger.twister`,
  which provides Trigger's remote execution functionality:

  - Added CLI support for Palo Alto Networks firewalls!
  - SSH Async now enabled by default for Arista, Brocade.
  - :feature:`54` Moved static definition of commands permitted to be
    executed when specified in a users' ``~/.gorc`` file into a new
    configuration setting :setting:`GORC_ALLOWED_COMMANDS`. The file
    location may now also be customized using :setting:`GORC_FILE`.
  - :bug:`68` Fix host lookup bug in `~trigger.twister.TriggerTelnet`
    causing telnet channels to crash.
  - :bug:`74` Fix error-detection for NetScaler devices.
  - Enhanced logging within `~trigger.twister` to include the device
    name where applicable and useful (such as in SSH channel
    debugging).
  - All ``execute_`` functions have been simplified to eliminate
    hard-coding of vendor checking wherever possible.
  - Beginnings of reworking of Generic vs. AsyncPTY SSH channels:

    * Most vendors support async/pty with little problems.
    * This will become the new default.
    * New execute helper: `~trigger.twister.execute_async_pty_ssh`
    * New error helper: `~trigger.twister.has_juniper_error`
    * Arista now uses `~trigger.twister.execute_async_pty_ssh`
    * A ``NetScalerCommandFailure`` will now just be a
      `~trigger.exceptions.CommandFailure`

+ Documentation

  - Updated README to callout CSV support.
  - Updated README to reflect branching model.
  - Updated supported vendors, and no longer promising NETCONF
    support.

.. _v1.3.0:

1.3.0
=====

.. warning::
   If you are upgrading from Trigger Before Upgrading from Trigger 1.2 or
   earlier, please heed these steps!

   + Add ``NETDEVICES_SOURCE = NETDEVICES_FILE`` to your ``settings.py``. This
     variable has replaced :setting:`NETDEVICES_FILE`.
   + Create your Bounce window mappings in ``bounce.py`` and put it in
     ``/etc/trigger/bounce.py``. See ``conf/bounce.py`` in the source
     distribution for an example.

+ General changes

  - All references to psyco have been removed as it doesn't support 64-bit and
    was causing problems in Python 2.7.3.
  - A new document, :doc:`new_vendors`, has been added to use as checklist for
    adding new vendor support to Trigger.
  - Added `Allan Feid <https://github.com/crazed>`_ as contributor for his
    *crazed* ideas.

+ :feature:`10` The following changes have been made within
  `~trigger.changemgmt`, which provides Trigger's support for bounce windows
  and timezones, to move the bounce window settings into configurable data vs.
  static in the module code.

  - This module has been convertd into a package.
  - The Bounce window API has been totally overhauled. Bounce windows are no
    longer hard-coded in `~trigger.changemgmt` and are now configured using
    ``bounce.py`` and specified using :setting:`BOUNCE_FILE`. The interface for
    creating `~trigger.changemgmt.BounceWindow` objects was greatly simplified
    to improve readability and usage.
   - Added sample ``bounce.py`` to ``conf/bounce.py`` in the Trigger source
     distribution.
   - New setting variables in ``settings.py``:

     - :setting:`BOUNCE_FILE` - The location of the bounce window mapping
       definitions. Defaults to ``/etc/trigger/bounce.py``.
     - :setting:`BOUNCE_DEFAULT_TZ` - Default timezone for bounce windows.
       Defaults to ``'US/Eastern'``.
     - :setting:`BOUNCE_DEFAULT_COLOR` - The default bounce risk-level status
       color. Defaults to ``'red'``.

+ :feature:`55` The following changes have been made within
  `~trigger.netdevices` to make it easier to populate
  `~trigger.netdevices.NetDevices` from arbitrary sources by implementing
  pluggable loaders.

  - This module has been converted into a package.
  - All hard-coded metadata parsing functions and associated imports have been
    replaced with loader plugin classes. Filesystem loaders provided by default
    for JSON, XML, Sqlite, Rancid, and *new*: CSV!). The bare minimum config for
    CSV is a newline-separated CSV file populated with "hostname,vendor"
  - New configuration setting: :setting:`NETDEVICES_LOADERS` used to define a
    list of custom loader classes to try in turn. The first one to return data
    wins.
  - The configuration settings :setting:`SUPPORTED_FORMATS` and
    :setting:`NETDEVICES_FORMAT` have been deprecated.
  - The configuration setting :setting:`NETDEVICES_SOURCE` has replaced
    :setting:`NETDEVICES_FILE`.
  - The sample ``settings.py`` (found at ``conf/trigger_settings.py`` in the
    source distribution) illustrates how one may use
    :setting:`NETDEVICES_SOURCE` and :setting:`NETDEVICES_LOADERS` to replace
    the deprecated settings :setting:`NETDEVICES_FORMAT` and
    :setting:`NETDEVICES_FILE`.

+ The following changes have been made within `~trigger.twister`, which
  provides Trigger's remote execution functionality:

  - :feature:`22` Added Aruba wireless controller and Brocade ADX/VDX support
    for execute/pty in trigger.twister and any device that requires pty-req and
    shell without actualling using a pty. The channel class for this
    functionality is called `~trigger.twister.TriggerSSHAsyncPtyChannel`
  - Added a new ``requires_async_pty`` attribute to
    `~trigger.netdevices.NetDevice` objects to help identify devices that
    require such channels.
  - Added a ``force_cli`` flag to `~trigger.twister.execute()` to force CLI
    execution on Juniper devices instead of Junoscript.
  - The default client factory (`~trigger.twister.TriggerClientFactory`) now
    calls `~trigger.tacacsrc.validate_credentials()` instead of directly
    instantiating `~trigger.tacacsrc.Tacacsrc` anytime credentials are
    populated automatically, resulting in only a single call to
    `~trigger.tacacsrc.Tacacsrc()`, when creds aren't provided.
  - Added error-detection for Brocade MLX devices.

+ The following changes have been made within `~trigger.cmds`, which provides
  an extensible, developer-friendly interface to writing command exeuction
  adapters:

  - Added a ``force_cli`` flag to `~trigger.cmds.Commando` constructor to force
    CLI execution on Juniper devices instead of Junoscript.
  - The ``timeout`` value may now be set as a class variable in
    `~trigger.cmds.Commando` subclasses.
  - `~trigger.cmds.Commando` now steps through ``commands`` as iterables instead
    of assuming they are lists. The iterable is also now explicitly cast to a
    list when we need it be one.
  - A minor bugfix in `~trigger.cmds.Commando` causing results from multiple
    Commando instances to collide with each other because they were inheriting
    an empty results ``{}`` from the class object.
  - `~trigger.cmds.Commando` now accepts ``creds`` as an optional argument. If
    not set, it will default to reading user credentials from ``.tacacsrc``.

+ The following changes have been madw within `~trigger.acl.parser`, which
  provides Trigger's support for parsing network access control lists (ACLs)
  and firewall policies.

  - :feature:`12` Support has been added for parsing IPv6 addresses in Juniper
    firewall filters. (This does not include full IPv6 firewall support!)
  - :bug:`26` The ACL parers was modified to support negation of addresses
    using the syntax ``{ip} except;`` in Juniper firewall filters. To
    facilitate this a custom IP address class was created:
    `~trigger.acl.parser.TIP` (which is a subclass of ``IPy.IP``).
  - The prefix on /32 and /128 IPs in Juniper ACLs is now always displayed.

+ The following changes have been made within `~trigger.tacacsrc`, which
  provides functionality to cache and retrieve user credentials:

  - Added a new function `~trigger.tacacsrc.validate_credentials()` to (you
    guessed it!) validate credentials. It supports input in the form 2-tuples
    (username, password), 3-tuples (username, password, realm), and
    dictionaries of the same and returns a `~trigger.tacacsrc.Credentials`
    object.

+ The following changes have been made to Trigger's command-line utilities:

  - :feature:`60` ``bin/load_acl`` will now shutdown gracefully if initial
    the MySQL connection fails, using a try..except to display some
    information about the connection failure without a traceback. For other
    MySQL issues, we will leave as is (dumping the traceback) because they
    would represent coding or transient issues, and we should present as much
    information as we have.
  - :feature:`20` ``bin/gnng`` (get_nets) In support of displaying Juniper
    'sp' interfaces (which are un-numbered and were being skipped for this
    reason), we've added flags to include un-numbered (``-u``) or disabled
    (``-d``) interfaces for any device platform.

.. _v1.2.4:

1.2.4
=====

+ The commands required to commit/save the configuration on a device are now
  attached to `~trigger.netdevices.NetDevice` objects under the
  `~trigger.netdevices.NetDevice.commit_commands` attribute, to make it easier
  to execute these commands without having to determine them for yourself.
+ :feature:`56` Added a way to optionally perform a ``commit full`` operation
  on Juniper devices by defining a dictionary of attributes and values for
  matching devices using :setting:`JUNIPER_FULL_COMMIT_FIELDS`. This modifies
  the ``commit_commands`` that are assigned when the
  `~trigger.netdevices.NetDevice` object is created.
+ :bug:`33` Console paging is now disabled by default for async SSH channels.

.. _v1.2.3:

1.2.3
=====

+ :feature:`47` Added parsing of ranges for ``fragment-offset`` statements in
  Juniper ACLs.
+ :bug:`49` Changed ACL parser to omit src/dst ports if port range is
  ``0-65535``.
+ :bug:`50` Fix typo that was causing Cisco parsing to generate an unhandled
  exception within `~trigger.cmds.NetACLInfo`.
+ Minor bugfix when checking device names and printing a warning within
  `~trigger.cmds.Commando`.
+ Updated docs to say we're using a interactive Python interpreter and added
  OpenHatch profile to contact info.

.. _v1.2.2:

1.2.2
=====

- :feature:`16` Arista support was added to ``bin/load_acl``
- :bug:`45` Added "SSH-1.99" as a valid SSHv2 version in
  `~trigger.utils.network.test_ssh()` to fix a bug in which devices presenting
  this banner were errantly falling back to telnet and causing weird behavior
  during interactive sessions.
- :feature:`46` Changed `~trigger.twister.connect()` to pass the vendor name to
  `~trigger.gorc.get_init_commands()` so that it is more explicit when
  debugging.
- :feature:`29` Added an extensible event notification system

  - A new pluggable notification system has been added in
    `~trigger.utils.notifications`, which defaults to email notifications.
    New event handlers and event types can be easily added and specified
    with the configuration using :setting:`NOTIFICATION_HANDLERS`.

  - The following changes have been made to ``bin/load_acl``:

    - All alerts are now using the new notification system
    - ``email_users()`` moved to `~trigger.utils.notifications.send_email()`
    - All calls to send failures now call
      `~trigger.utils.notifications.send_notification()`
    - All calls to send successes now calls
      `~trigger.utils.notifications.send_email()`

  - In support of the new notification system, the following config
    settings have been added:

    - :setting:`EMAIL_SENDER` - The default email sender
    - :setting:`NOTIFICATION_SENDER` - The default notification sender
    - :setting:`SUCCESS_RECIPIENTS` - Hosts/addresses to send successes
    - :setting:`FAILURE_RECIPIENTS` - Hosts/addresses to send failures
    - :setting:`NOTIFICATION_HANDLERS` - A list of handler functions to
      process in order

  - A new utility module has been added to import modules in
    `~trigger.utils.importlib`, and ``trigger.conf.import_path()`` was moved to
    `~trigger.utils.importlib.import_module_from_path()` to bring these import
    tools under one roof.

.. _v1.2.1:

1.2.1
=====

- :bug:`30` Bugfix in ``bin/acl`` where tftproot was hard-coded. It now reads
  from :setting:`TFTPROOT_DIR`.
- :feature:`37` Fixed misleading "make discard" output from
  ``bin/check_access``, to use the ``Term.extra`` attribute to store a
  user-friendly comment to make it clear that the term's action has been
  modified by the "make discard" keyword.
- :feature:`39`  Call ``create_cm_ticket()`` in a ``try..commit`` block so it
  can't crash ``bin/load_acl``.
- :bug:`40` Update dot_gorc.example with ``[init_commands]``.
- :bug:`43` Bugfix in bin/acl to address incorrect exception reference from
  when exceptions were cleaned up in release 1.2.
- Simplified basic `~trigger.cmds.Commando` example in ``docs/index.rst``.
- Simplified activity output in `~trigger.cmds.Commando` base to/from methods
- Replaced all calls to ``time.sleep()`` with ``reactor.callLater()`` within
  `~trigger.twister` support of the ``command_interval`` argument to Twisted
  state machine constructors.
- Added a way to do SSH version detection within `~trigger.utils.network`

  - Enhanced `~trigger.utils.network.test_tcp_port()` to support optional
    ``check_result`` and ``expected_result`` arguments. If ``check_result`` is
    set, the first line of output is retreived from the connection and the
    starting characters must match ``expected_result``.
  - Added a `~trigger.utils.network.test_ssh()` function to shortcut to check
    port 22 for a banner. Defaults to SSHv2.
  - SSH auto-detection in `~trigger.netdevices.NetDevices` objects now uses
    `~trigger.utils.network.test_ssh()`.

- Added a new `~trigger.utils.crypt_md5()` password-hashing function.
- Added proper argument signature to `~trigger.acl.db.get_netdevices`.
- Updated misnamed ``BadPolicerNameError`` to `~trigger.exceptions.BadPolicerName`
- More and better documentation improvements, including new documentation for
  ``bin/acl_script``.

.. _v1.2:

1.2
===

- :feature:`23` Commando API overhauled and support added for RANCID

  - RANCID is now officially supported as a source for network device
    metadata. A new RANCID compatibility module has been added at
    `~trigger.rancid`, with support for either single or multiple instance
    configurations. Multiple instances support can be toggled by setting
    :setting:`RANCID_RECURSE_SUBDIRS` to ``True``.

  - The following changes have been made to `~trigger.netdevices`:

    - `~trigger.netdevices.NetDevices` can now import from RANCID
    - A new `~trigger.netdevices.Vendor` type has been added to
      `~trigger.netdevices` to store canonical vendor names as determined by
      the new setting :setting:`VENDOR_MAP`.
    - When `~trigger.netdevice.NetDevice` objects are created, the manufacturer
      attribute is mapped to a dynamic vendor attribute. This is intended to
      normalize the way that Trigger identifies vendors internally by a single
      lower-cased word.
    - All `~trigger.netdevices.NetDevice` objects now have a ``vendor``
      attribute with their canonical `~trigger.netdevices.Vendor` object
      attached to it.
    - If the ``deviceType`` attribute is not set, it is determined
      automatically based on the ``vendor`` attribute. The default types for
      each vendor can be customized using :setting:`DEFAULT_TYPES`. If a vendor
      is not specified witihin :setting:`DEFAULT_TYPES`,
      :setting:`FALLBACK_TYPE`. will be used.
    - All logical comparisons that onced used the hard-coded value of the
      ``manufacturer`` attribute of a device now instead compare against the
      ``vendor`` attribute.
    - You may now tell NetDevices not to fetch acls from AclsDB when
      instantiate you may also do the same for individual NetDevice objects
      that you manually create

  - The following changes have been made to `~trigger.cmds`:

    - The `~trigger.cmds.Commando` class been completely redesigned to reduce
      boilerplate and simplify creation of new command adapters. This is
      leveraging the changes to `~trigger.netdevice.NetDevice` objects, where
      the vendor name can be expected to always be normalized to a single,
      lower-cased word. Defining commands to send to devices is as simple as
      definiing a ``to_{vendor}`` method, and parsing return results as simple
      as ``from_{vendor}``.
    - All dynamic method lookups are using the normalized vendor name (e.g.
      cisco, juniper).
    - Base parse/generate lookup can be disabled explicitly in
      `~trigger.cmds.Commando` subclasses or as an argument to the constructor.
    - `~trigger.cmds.NetACLInfo` adapted to use Commando 2.0

  - The following changes have been made to Trigger's exception handling

    - All exceptions moved to `~trigger.exceptions` and given docstrings
    - ``trigger.acl.exceptions`` has been removed
    - All calls to exceptions updated to new-style exceptions

  - A new -v option has been added to ``bin/netdev`` to support vendor lookups

- :feature:`4` Support for SSH auto-detection and pty/async improvements:

  - The following changes have been made to `~trigger.twister`:

    - Detection of remotely closed SSH connections so ``bin/gong`` users can be
      properly notified (e.g. ssh_exchange_identification errors)
    - New `~trigger.twister.execute` function to automatically choose the best
      ``execute_`` function for a given `~trigger.netdevices.NetDevice` object,
      and is now attached to all `~trigger.netdevices.NetDevice` objects
    - `~trigger.twister.execute_ioslike` now determines whether to use SSH or
      Telnet automatically
    - All pty connection logic moved out of ``bin/gong`` into
      `~trigger.twister` and is exposed as the `~trigger.twister.connect`
      function and also attached to all `~trigger.netdevices.NetDevice` objects
    - Interactive sessions may now be optionally logged to a file-like object by
      passing the log_to argument to the `~trigger.twister.Interactor`
      constructor
    - `~trigger.twister.execute_junoscript` now using
      `~trigger.twister.execute_generic_ssh`
    - Command interval added to Junoscript channels for consistency
    - Global `~trigger.netdevices.NetDevices` import removed from twister;
      moved to only occur when a telnet channel is created

  - The following changes have been made to `~trigger.netdevices`:

    - All `~trigger.netdevices.NetDevice` objects now have a
      `~trigger.twister..execute` method to perform async interaction
    - The `~trigger.twister.connect` function is now automatically attached to
      every `~trigger.netdevices.NetDevice` object; to get a pty it's as simple
      as ``dev.connect()``.
    - New helper methods added to `~trigger.netdevices.NetDevice` objects:

      - SSH functionality methods: `~trigger.netdevices.NetDevice.has_ssh()`
        (port connection test), `~trigger.netdevices.NetDevice.can_ssh_async()`
        (device supports async), `~trigger.netdevices.NetDevice.can_ssh_pty()`
        (device supports pty)
      - `~trigger.netdevices.NetDevice.is_ioslike()` to test if a device is
        IOS-like as specified by :setting:`IOSLIKE_VENDORS`.
      - `~trigger.netdevices.NetDevice.is_netscreen` to test if a device is a
        NetScreen firewall
      - `~trigger.netdevices.NetDevice.is_reachable` to test if a device
        responds to a ping

  - The following changes have been made to `~trigger.conf.settings`:

    - A mapping of officially supported platforms has been defined at
      :setting:`SUPPORTED_PLATFORMS`
    - :setting:`VALID_VENDORS` has been renamed to :setting:`SUPPORTED_VENDORS`
    - A mapping of officially supported device types has been defined at
      :setting:`SUPPORTED_TYPES`
    - You may now disable telnet fallback by toggling :setting:`TELNET_ENABLED`
    - You may now disable SSH for pty or async by vendor/type using
      :setting:`SSH_PTY_DISABLED` and :setting:`SSH_ASYNC_DISABLED`
      respectively
    - :setting:`SSH_TYPES` has been removed as it is no longer needed

  - `~trigger.cmds.Commando` experimentally using the new
    ``NetDevice.execute()`` method
  - Two new helper functions added to `~trigger.utils.cli`:
    `~trigger.utils.cli.setup_tty_for_pty` and
    `~trigger.utils.cli.update_password_and_reconnect`, which modularize
    functionality that was in bin/gong that didn't seem to fit anywhere else

- :feature:`21` The following changes have been made to support A10 hardware
  and to enhance handling of SSH channels:

  - Added a new generic SSH channel. The NetScreen and A10 channels are based
    from this. Further abstraction needed to roll NetScaler channel into this
    as well.
  - Added a new `~trigger.twister.execute_generic_ssh` factory function.
  - Refactored `~trigger.twister.execute_netscreen` to use `~trigger.twister.execute_generic_ssh`
  - Added a new `~trigger.twister.execute_ioslike_ssh` factory function
    utilizing the generic SSH channel to support SSH on IOS-like devices
    (Brocade, Cisco, Arista, A10, etc.). Works like a charm except for the
    Brocade VDX.
  - The `~trigger.cmds.Commando` was updated to support A10, NetScreen. Brocade,
    Arista changed to use SSH vs. telnet.
  - All prompt-matching patterns moved to top of `trigger.twister` as constants
  - A10 added to :setting:`IOSLIKE_VENDORS`

- :feature:`24` ``bin/gong`` will now display the reason when it fails to
  connect to a device.

.. _v1.1:

1.1
===

- All changes from release 1.0.0.100 (oh hey, duh) are officially part of this
  release
- :bug:`9` Fixed missing imports from ``bin/acl_script`` and removed a bunch of
  duplicated code already within the Trigger libs.
- Added new keywords to setup.py
- Some new utilities added to `~trigger.acl.tools` for merging new access into
  an existing ACL object
- :feature:`17` `~trigger.acl.parser.RangeList` now sorts port range tuples
  when parsing access-lists.
- :bug:`8` `~trigger.tacacsrc.get_device_password` user-friendly message moved
  to `~trigger.twister.pty_connect` so it no longer bleeds into
  non-interactive usage.
- :bug:`15` `~trigger.acl.parser.Term.output_ios` updated to support optional
  ``acl_name`` argument for cases when you need to output a
  `~trigger.acl.parser.Term` separately from an `~trigger.acl.parser.ACL`
  object. `~trigger.acl.tools.check_access`, ``bin/check_access``, and
  ``bin/find_access`` also had to be updated to utilize this new argument.
- :bug:`19` `~trigger.acl.tools.check_access` updated to support 'complicated'
  checks against Juniper firewall terms with a 'port' statement defined.

1.0.0.100
=========

- `~trigger.conf` converted from a module to a package.
- All global default settings are now baked into trigger.conf.settings
- `~trigger.conf.settings` and `~trigger.acl.autoacl` may now be imported without the
  proper expected config files in place on disk. If the config files cannot be
  found, default versions of these objects will be returned.
- All trigger modules can now be imported with default values (but don't try
  instantiating any objects without following the install instructions!)
- :bug:`2` Fixed a bug in :class:`~trigger.tacacsrc.Tacacsrc` where newly-created
  .tacacsrc files were world-readable. Correct 0600 perms are now enforced on
  every write().
- :feature:`3` Added the ability for :class:~trigger.twister.IoslikeSendExpect`
  to handle confirmation prompts (such as when a device asks you "are you sure?
  [y/N]:" by detecting common cases within the prompt-matching logic.
- :feature:`5` Added ability for gong --oob to lookup devices by partial
  hostnames using :func:`~trigger.netdevices.device_match`.
- :bug:`6` The `get_firewall_db_conn()` function was moved out of `settings.py`
  and into `~trigger.acl.queue.Queue` where it belongs.
- :feature:`7` Updated :func:`~trigger.twister.has_ioslike_error` to support
  Brocade VDX errors.


1.0.0.90
========

- Added support for .gorc file to specify commands to run when using gong to
  login to a device. Unique commands cand be specified for each vendor.
- Default realm for credentials within .tacacsrc can now be specified within
  settings.DEFAULT_REALM
- The following changes have been made to trigger.tacacsrc:

  - New module-level update_credentials() function added to facilitate updating of
    cached user credentials by client applications (e.g. gong)
  - Renamed the exceptions within trigger.tacacsrc to be more human-readable
  - Tacacsrc._parse_old() completely redesigned with real error-handling for
    bad/missing passwords (GPG-parsing coming "Soon")
  - New Tacacsrc.update_creds() method used to facilitate update of stored
    credentials within .tacacsrc
  - Realm is now stored as an attribute on Credentials objects to simplify
    loose-coupling of device/realm information while passing around
    credentials.
  - prompt_credentials() refactored to be more user-friendly.
  - Blank passwords can no longer be stored within .tacacsrc.

- The following changes have been made to trigger.twister:

  - trigger.twister internals have been updated to support the passing of a
    list of initial_commands to execute on a device upon logging in.
  - TriggerClientFactory now reads the default realm from
    settings.DEFAULT_REALM when populating credentials.
  - TriggerClientFactory credentials detection improved
  - All referencing of username/password from credentials by index replaced
    with attributes.
  - Failed logins via telnet/ssh will now raise a LoginFailure exception that
    can be handled by client applications (such as gong)

- bin/gong now detects login failures and prompts users to update their cached
  password.

1.0.0.80
========

- Typo fix in sample conf/trigger_settings.py
- Explicit imports from trigger.acl and a little docstring cleanup in bin/optimizer
- trigger.acl.autoacl.autoacl() now takes optional explicit_acls as 2nd
  argument, a set of ACL names, so that we can reference explicit_acls within
  autoacl() implicit ACL logic, but we don't have to rely on the internals.
- trigger.acl.db.AclsDB.get_acl_set() modified to populate explicit_acls before
  implicit_acls. autoacl() is now called with these explicit_acls as the 2nd
  argument.
- Sample autoacl.py in conf/autoacl.py updated to support explicit_acls and a
  simple example of how it could be used.
- Added support for Juniper "family inet" filters in trigger.acl.parser.
- ACL objects now have a family attribute to support this when constructed or
  parsed using the .output_junos() method.

1.0.0.70
========

- Minor bugfix in trigger.netdevices._parse_xml()

1.0.0.60
========

- New nd2json.py nad nd2sqlite.py tools for use in converting existing
  netdevices.xml implementations
- Added sample netdevices.json in conf/netdevices.json
- Added SQLite database schema for netdevices in conf/netdevices.sql

1.0.0.50
========

- New NetDevices device metadata source file support for JSON, XML, or SQLite3
- Companion changes made to conf/trigger_settings.py
- trigger.netdevice.NetDevice objects can now be created on their own and have
  the minimum set of attributes defaulted to None upon instantiation

1.0.0.40
========

- Public release!
- Arista and Dell command execution and interactive login support in trigger.twister!

Legacy Versions
===============

Trigger was renumbered to version 1.0 when it was publicly released on April 2,
2012. This legacy version history is incomplete, but is kept here for posterity.

1.6.1
-----

- Users credentials from tacacsrc.Tacacsrc are now stored as a namedtuple aptly
  named 'Credentials'

1.6.0 - 2011-10-26
------------------

- Fixed missing acl.parse import in bin/find_access
- More documentation cleanup!
- The following changes have been made to trigger.cmds.Commando:

  - Added parse/generate methods for Citrix NetScaler devices
  - Renamed Commando.work to Commando.jobs to avoid confusing inside of
    Commando._add_worker()
  - Added distinct parse/generate methods for each supported vendor type (new:
    Brocade, Foundry, Citrix)
  - Generate methods are no longer called each time _setup_callback() is
    called; they are now called once an entry is popped from the jobs queue.
  - All default parse/generate methods now reference base methods to follow DRY
    in this base class.

- Fixed incorrect IPy.IP import in bin/acl_script

- Trigger.twister.pty_connect will only prompt for distinct passwors on firewalls
- Added _cleanup() method to acl.parser.RangeList objects to allow for addition
  of lists of mixed lists/tuples/digits and still account for more complex
  types such as Protocol objects
- Performance tweak to Rangelist._expand() method for calculating ranges.

- Added parsing support for remark statements in IOS numbered ACLs

1.5.9 - 2011-08-17
------------------

- Tons and tons of documentation added into the docs folder including usage,
  API, and setup/install documentation.
- Tons of code docstrings added or clarified across the entire package.
- Added install_requires to setup() in setup.py; removed bdist_hcm install command.
- The following changes have been made to trigger.twister:

  - Massive, massive refactoring.
  - New base class for SSH channels.
  - New NetScaler SSH channel. (Full NetScaler support!)
  - New execute_netscaler() factory function.
  - execute_netscreenlike() renamed to execute_netscreen().
  - Every class method now has a docstring.
  - Many, many things moved around and organized.

- Added doctsrings to trigger.netdevices.NetDevice class methods
- The following CLI scripts have been removed from Trigger packaging to an internal
  repo & removed from setup.py. (These may be added back after further internal
  code review.)

  - bin/acl_mass_delete
  - bin/acl_mass_insert
  - bin/fang
  - bin/get_session
  - bin/merge_acls

- The following CLI scripts have had their documentation/attributions updated:

  - bin/fe
  - bin/gong
  - bin/load_acl

- Restructuring within bin/load_acl to properly abstract fetching of on-call
  engineer data and CM ticket creation into trigger_settings.py.
- External release sanitization:

  - Template for trigger_settings.py updated and internal references removed.
  - Sanitized autoacl.py and added generic usage examples.

- The following items have been moved from bin/load_acl into trigger.utils.cli:

  - NullDevice, print_severed_head, min_sec, pretty_time.

- Fixed a bug in trigger.utils.rcs.RCS that would cause RCS log printing to fail.
- Added REDIS_PORT, REDIS_DB to trigger_settings.py and tweaked trigger.acl.db to support it.
- Fixed bug in bin/netdev causing a false positive against search options.
- trigger.netscreen: Tweak EBNF slightly to parse policies for ScreenOS 6.x.

1.5.8 - 20011-06-08
-------------------

- trigger.acl.parser fully supports Brocade ACLs now, including the ability to strip comments and properly
  include the "ip rebind-receive-acl" or "ip rebind-acl" commands.
- trigger.acl.Term objects have a new output_ios_brocade() method to support Brocade-special ACLs
- bin/load_acl will automatically strip comments from Brocade ACLs

1.5.7 - 2011-06-01
------------------

- Where possible replaced ElementTree with cElementTree for faster XML parsing
- New NetDevices.match() method allows for case-insensitive queries for devices.
- NetDevices.search() now accepts optional field argument but defaults to nodeName.
- New trigger.acl.ACL.strip_comments() method ... strips... comments... from ACL object.
- bin/fang:

  - Now accepts hostnames as arguments
  - Now *really* properly parses hops on Brocade devices.

- bin/load_acl:

  - Now fully supports Brocade devices.
  - Strips comments from Brocade ACLs prior to staging and load.
  - Now displays temporary log file location to user.

- Removed jobi, orb, nms modules from Trigger; replaced with python-aol versions.

1.5.6 - 2011-05-24
------------------

- bin/acl: corrected excpetion catching, changes option help text and made -a and -r append
- bin/gnng, bin/netdev: Added -N flag to toggle production_only flag to NetDevices
- trigger.cmds/trigger.twister: Added support for 'BROCADE' vendor (it's ioslike!)
- trigger.cmds.Commando: All generate_* methods are now passed a device object as the first argument
  to allow for better dynamic handling of commands to execute
- bin/fang: Can now properly parse hops on Brocade devices.

1.5.5 - 2011-04-27
------------------

- bin/acl: Will now tell you when something isn't found
- bin/acl: Added -q flag to silence messages if needed
- get_terminal_width() moved to trigger.utils.cli
- trigger.tacacsrc: Fixed bogus AssertionError for bad .tacacsrc file. Clarified error.
- trigger.twister: Fixed bug in Dell password prompt matching in execute_ioslike()
- bin/fang: Increased default timeout to 30 seconds when collecting devices.
- trigger.cmds.Commando:

  - Replaced all '__foo()' with '_foo()'
  - Removed Commando constructor args that are not used at this time
  - Added production_only flag to Commando constructor

1.5.4 - 2011-03-09
------------------

- Fixed a bug in trigger.cmds.Commando that would prevent reactor loop from
  continuing after an exception was thrown.
- trigger.cmds.Commando now has configurable timeout value (defaults to 30
  seconds)
- trigger.acl.tools now looks at acl comments for trigger: make discard
- fixed a bug with gong connecting to devices' oob

1.5.3 - 2011-01-12
------------------

- Fixed a bug in trigger.cmds.NetACLInfo where verbosity was not correctly
  toggled.
- gong (go) will now connect to non-prod devices and throw a warning to the
  user
- gong can connect to a device through oob by passing the -o or --oob option.
- acl will make any device name lower case before associating an acl with it.

1.5.2 - 2010-11-03
------------------

- bin/find_access: Added -D and -S flags to exclude src/dst of 'any' from
  search results. Useful for when you need to report on inclusive networks but
  not quite as inclusive as 0.0.0.0/0.
- Fixed a bug in acls.db where a device without an explicit association would
  return None and throw a ValueError that would halt NetDevices construction.
- Added __hash__() to NetDevice objects so they can be serialized (pickled)
- Fixed a bug in explicit ACL associations that would sometimes return
  incorrect results
- trigger.cmds.NetACLInfo now has a verbosity toggle (defaults to quiet)
- Caught an exception thrown in NetACLInfo for some Cisco devices

1.5.1 - 2010-09-08
------------------

- trigger.conf: import_path() can now be re-used by other modules to load
  modules from file paths without needing to modify sys.path.
- autoacl can now be loaded from a location specified in settings.AUTOACL_FILE
  allowing us to keep the ever-changing business rules for acl/device mappings
  out of the Trigger packaging.
- netdevices:

  - Slight optimization to NetDevice attribute population
  - Added new fields to NetDevice.dump() output
  - All incoming fields from netdevices.xml now normalized

- bin/netdev:

  - added search option for Owning Team (-o)
  - search opt for OnCall Team moved to -O
  - search opt for Owning Org (cost center) moved to -C
  - added search option for Budget Name (-B)
  - refactored search argument parsing code

- bin/fang:

  - will now not display information for ACLs found in settings.IGNORED_ACLS

1.5.0r2 - 2010-08-16
--------------------

- Minor fix to warnings/shebang for bin/scripts

1.5.0 - 2010-08-04
------------------

- acl.db: renamed ExplicitACL to AclsDB, all references adjusted
- process_bulk_loads() moved to trigger.acl.tools
- get_bulk_acls() moved to trigger.acl.tdb
- get_all_acls(), get_netdevices(), populate_bulk_acls() added to trigger.acl.db
- load_acl: now imports bulk_acl functions from trigger.acl.tools
- load_acl: now uses trigger.acl.queue API vs. direct db queries
- load_acl: --bouncy now disables bulk acl thresholding
- load_acl: now displays CM ticket # upon successful completion
- process_bulk_loads() now uses device.bulk_acl associations, better performance
- device_match() now sorts and provides correct choices
- Juniper filter-chain support added to trigger.cmds.NetACLInfo
- gnng updated to use NetACLinfo
- Added proceed() utility function trigger.utils.cli
- Several ACL manipulation functions added to trigger.acl.tools:

  - get_comment_matches() - returns ACL terms comments matching a pattern
  - update_expirations() - updates expiration date for listed ACL terms
  - write_tmpacl() - writes an ACL object to a tempfile
  - diff_files() - returns a diff of two files
  - worklog() - inserts a diff of ACL changes into the ACL worklog

- fang: patched to support Juniper filter-lists

1.4.9r2 - 2010-04-27
--------------------

- find_access: Corrected missing import for IPy
- tacacsrc.py: Corrected bug with incorrect username association to .tacacsrc in sudo/su
  use-cases (such as with cron) where login uid differs from current uid.

1.4.9 - 2010-04-26
------------------

- You may now use gong (go) to connect to Dell devices (telnet only).
- Completely overhauled tacacsrc.py to support auto-detection of missing .tacacsrc
- Heavily documented all changes to tacacsrc.py
- Twister now imports from tacacsrc for device password fetching
- gen_tacacsrc.py now imports from tacacsrc for .tacacsrc generation
- load_acl now uses get_firewall_db_conn from global settings
- Added new search() method to NetDevices to search on name matches
- Added a new device_match() function to netdevices for use with gong
- gong now uses device_match() to present choices to users
- netdev now uses device_match() to present choices to users

1.4.8 - 2010-04-16
------------------

- acls.db replaced with redis key/value store found at trigger.acl.db
- trigger.acl converted to package
- all former trigger.acl functionality under trigger.acl.parser
- autoacls.py moved to trigger.acl.autoacls
- aclscript.py moved to trigger.acl.tools.py
- netdevices.py now using trigger.acl.db instead of flat files
- added trigger.netdevices.NetDevices.all() as shortcut to itervalues()
- You may now use gong (go) to connect to non-TACACS devices, such as OOB or
  unsupported devices using password authentication.
- The ACL parser has been reorganized slightly to make future modifications
  more streamlined.
- Load_acl now logs *all* activity to a location specified in Trigger config file.
- Added new 'trigger.utils' package to contain useful modules/operations
- 'acl' command moved into Trigger package
- 'netdev' command moved into Trigger package
- Merged trigger.commandscheduler into trigger.nms
- Basic trigger_settings.py provided in conf directory in source dist.
