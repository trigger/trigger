=========
Changelog
=========

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
2012. This legacy version history is incompleted, but is kept here for posterity.

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
