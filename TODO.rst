==================
Trigger To Do List
==================

Things we want to fix:

+ Replace MySQL w/ a real task queue (Celery backed by Redis?)

+ Move get_tftp_source() from bin/load_acl to trigger.acl.tools

+ Pull out all guts for "old password hashing" method from trigger.tacacsrc and make GPG auth the default. Also make sure the setup and install of this is properly documented

+ Move settings.IGNORED_ACLS into Redis and maintain it with the bin/acl command

+ Overhaul the way that bulk ACL loading/thresholding is done. Replace with a percentage-based system, rather than static numbers.

+ Improve the interface to settings.create_cm_ticket() so that it is more intuitive.

+ Implement SSH support in trigger.twisted.execute_ioslike()

+ Find a way to dynamically generate or call instance methods for trigger.cmds.Commando for multiple and future network hardware vendor support.

+ Implement real unit tests. They are horrendously out of date. Most new features have no tests.
