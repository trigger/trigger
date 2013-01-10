=============================
Adding New Vendors to Trigger
=============================

This is a work in progress. Please bear with us as we expand and improve this
documentation. If you have any feedback, please don't hesitate to `contact us
<http://trigger.readthedocs.org/en/latest/index.html#getting-help>`_!!

.. contents::
    :local:
    :depth: 2

Checklist
=========

You need to account for the following:

Interactive (pty) sessions 
--------------------------

+ Does it support telnet?
+ Does it support SSH? (Should work by default)
+ What is the SSH auth method? (keyboard-interactive, password, etc.)

Async factory method (execute_) for remote execution
----------------------------------------------------

+ For telnet: Can you use IoslikeSendExpect state machine?
+ For SSH:

  - Does it support SSH exec? Try execute_exec_ssh
  - Does it support SSH shell? Try execute_generic_ssh

+ What is the prompt pattern? 
+ What is the command to disable paging?

  - add 'vendor_name': 'disable paging command\n' to trigger.netdevices.NetDevice._set_startup_commands.paging_map dictionary.

+ What is the command to commit/write to memory?

  - Account for 'vendor_name' in trigger.netdevices.NetDevice._set_commit_commands

Commando support
----------------

Add the vendor name to the following:

- add 'vendor_name' to settings.SUPPORTED_VENDORS
- add 'VENDOR INTERAL NAME': 'vendor_name' to settings.VENDOR_MAP
- add 'vendor_name': ['DEVICE_TYPE'] to settings.SUPPORTED_PLATFORMS
- add 'vendor_name': 'DEVICE_TYPE' to settings.DEFAULT_TYPES
- add 'vendor_name' to settings.IOSLIKE_VENDORS

Error messages/timeouts 
-----------------------

Determine how error messages are displayed, and what default timeouts (if any) need to be accounted for.

Example::

    "% Invalid input detected at '^' marker."
