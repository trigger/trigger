
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

+ :feature:`10` The following changes have been made within `~trigger.changemgmt`, which
  provides Trigger's support for bounce windows and timezones, to move the
  bounce window settings into configurable data vs. static module. 

  - The Bounce window API totally overhauled. Bounce windows are no longer
    hard-coded in `~trigger.changemgmt` and are now configured using
    ``bounce.py`` and specified using :setting:`BOUNCE_FILE`. The interface for
    creating `~trigger.changemgmt.BounceWindow` objects was greatly simplified
    to improve readability and usage.
   - Added sample ``bounce.py`` to ``conf/bounce.py`` in source distribution
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
  
  - The module has been converted into a package.
  - All hard-coded metadata parsing functions and associated imports have been
    replaced with loader plugin classes. Filesystem loaders provided by default
    for JSON, XML, Sqlite, Rancid, and *new*: CSV!). The bare minimum config for
    CSV is a newline-separated CSV file populated with "hostname,vendor"
  - New configuration setting: :setting:`NETDEVICES_LOADERS` used to define a
    list of custom loader classes to try in turn. The first one to return data
    wins.
  - The configuration settings :setting:`SUPPORTED_FORMATS` and
    :setting:`NETDEVICES_FORMAT`  have been deprecated.
  - The configuration setting :setting:`NETDEVICES_SOURCE` has replaced
    :setting:`NETDEVICES_FILE`.
  - The sample ``settings.py`` (found at ``conf/trigger_settings.py`` in the
    source distribution) is illustrates how one may use
    :setting:`NETDEVICES_SOURCE` and :setting:`NETDEVICES_LOADERS` to replace
    the deprecated settings :setting:`NETDEVICES_FORMAT` and
    :setting:`NETDEVICES_FILE`.

+ The following changes have been made within `~trigger.twister`, which
  provides Trigger's remote execution functionality:

  - :feature:`22` Add Aruba wireless controller and Brocade ADX/VDX support for
    execute/pty in trigger.twister and any device that requires pty-req and
    shell without actualling using a pty. The channel class for this
    functionality is called `~trigger.twister.TriggerSSHAsyncPtyChannel`
  - Added a new ``requires_async_pty`` attribute to
    `~trigger.netdevices.NetDevice` objects to help identify devices that
    require such channels.
  - Added a ``force_cli`` flag to `~trigger.twister.execute()` to force CLI
    execution on Juniper devices instead of Junoscript.
  - The default client factory (`~trigger.twister.TriggerClientFactory`) now
    calls `~trigger.tacacsrc.validate_credentials()` instead of directly
    instantiating `~tacacsrc.Tacacsrc` anytime credentials are populated
    automatically, resulting in only a single call to `~tacacsrc.Tacacsrc()`,
    when creds aren't provided.
  - Added error-detection for Brocade MLX.

+ The following changes have been made within `~trigger.cmds`, which provides
  an extensible, developer-friendly interface to writing command exeuction
  adapters. 

  - Added a ``force_cli`` flag to `~trigger.cmds.Commando` constructor to force
    CLI execution on Juniper devices instead of Junoscript.
  - The ``timeout`` value may now be  to be set as a class variable in
    `~trigger.cmds.Commando` subclasses.
  - `~trigger.cmds.Commando` now step through ``commands`` as iterables instead
    of assuming they are lists. The iterable is also now explicitly cast to a
    list when we need them it be one.
  - A minor bugfix in ~trigger.cmds.Commando` causing results from multiple
    Commando instances to collide with each other because they were inheriting
    an empty results ``{}`` from the class object.
  - `~trigger.cmds.Commando` now accepts ``creds`` as an optional argument. If
    not set, it will default to reading user credentials from ``.tacacsrc``.

+ The following changes have been madw within `~trigger.acl.parser`, which
  provides Trigger's support for parsing network access control lists (ACLs)
  and firewall policies.

  - :feature:`12` Support has been added for parsing IPv6 addresses in Juniper
    firewall filters.
  - :bug:`26` Parsing of "{ip} except;" in Junos ACLs doesn't seem to be
    functioning. Parser modifications to support negation of address in Junos
    ACLs.
  - Always display the prefix on /32 and /128 IPs in Juniper ACLs.

+ The following changes have been made within `~trigger.tacacsrc`, which
  provides functionality to cache and retrieve user credentials:

  - Added a new function `~trigger.tacacsrc.validate_credentials()` validate
    credentials in the form of supports 2-tuples (username, password), 3-tuples
    (username, password, realm), and dictionaries of the same and returns a
    `~trigger.tacacsrc.Credentials` object.

+ The following changes have been made to Trigger's command-line utilities:

  - :feature:`60` ``bin/load_acl`` will now shutdown gracefully if initial
    MySQL connection doesn't work, using a try..except to display some
    information about the connection failure without a traceback. For other
    MySQL issues, we will leave as is (dumping the traceback) because they
    would represent coding or transient issues, and we should present as much
    information as we have.
  - :feature:`20` ``bin/gnng`` (get_nets) now supports not only support Juniper
    'sp' interfaces, but we've added flags to include un-numbered (``-u``) or
    disabled (``-d``) interfaces.
