# Trigger To Do List

Things we want to fix.

## Big Things

+ Document the NetDevices data structure and all base attributes expected to be
  found within a NetDevice object.

+ Replace MySQL w/ a real task queue (Celery backed by Redis?)

+ Pull out all guts for "old password hashing" method from trigger.tacacsrc and
  make GPG auth the default. Also make sure the setup and install of this is
  properly documented

+ Overhaul the way that bulk ACL loading/thresholding is done. Replace with a
  percentage-based system, rather than static numbers.

+ Find a way to dynamically generate or call instance methods for
  trigger.cmds.Commando for multiple and future network hardware vendor
  support.

+ Implement SSH support in trigger.twisted.execute_ioslike()

## Little Things

+ Move get_tftp_source() from bin/load_acl to trigger.acl.tools

+ Move settings.IGNORED_ACLS into Redis and maintain it with the bin/acl command

+ Improve the interface to settings.create_cm_ticket() so that it is more
  intuitive and properly documented.

## Non-Trivial Things

+ Implement real unit tests. They are horrendously out of date. Most new
  features have no tests.
