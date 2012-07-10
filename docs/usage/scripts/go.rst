=====================
go - Device connector
=====================

.. contents::
    :local:
    :depth: 2

About
=====

**go** Go connects to network devices and automatically logs you in using
cached TACACS credentials. It supports telnet, SSHv1/v2.

**PLEASE NOTE:** **go** is still named **gong** (aka "Go NG") within the
Trigger packaging due to legacy issues with naming conflicts. This will be
changing in the near future.

Usage
=====

Here is the usage output::

    % gong
    Usage: gong [options] [device]

    Automatically log into network devices using cached TACACS credentials.

    Options:
      -h, --help  show this help message and exit
      -o, --oob   Connect to device out of band first.


Examples
========

Caching credentials
-------------------

If you haven't cached your credentials, you'll be prompted to::

    % gong test2-abc
    Connecting to test2-abc.net.aol.com.  Use ^X to exit.
    /home/jathan/.tacacsrc not found, generating a new one!

    Updating credentials for device/realm 'tacacsrc'
    Username: jathan
    Password:
    Password (again):

    Fetching credentials from /home/jathan/.tacacsrc
    test2-abc#

This functionality is provided by :class:`~trigger.tacacsrc.Tacacsrc`.

Connecting to devices
---------------------

Using gong is pretty straightforward if you've already cached your credentials::

    % gong test1-abc
    Connecting to test1-abc.net.aol.com.  Use ^X to exit.

    Fetching credentials from /home/jathan/.tacacsrc
    --- JUNOS 10.0S8.2 built 2010-09-07 19:55:32 UTC
    jathan@test1-abc>

Full or partial hostname matches are also acceptable::

    % gong test2-abc.net.aol.com
    Connecting to test2-abc.net.aol.com.  Use ^X to exit.

If there are multiple matches, you get to choose::

    % gong test1
    3 possible matches found for 'test1':
     [ 1] test1-abc.net.aol.com
     [ 2] test1-def.net.aol.com
     [ 3] test1-xyz.net.aol.com
     [ 0] Exit

    Enter a device number: 3
    Connecting to test1-xyz.net.aol.com.  Use ^X to exit.

If a partial name only has a single match, it will connect automatically::

    % gong test1-a
    Matched 'test1-abc.net.aol.com'.
    Connecting to test1-abc.net.aol.com.  Use ^X to exit.

Out-of-band support
-------------------

If a device has out-of-band (OOB) terminal server and ports specified within
:class:`~trigger.netdevices.NetDevices`, you may telnet to the console by using
the ``-o`` flag::

    % gong -o test2-abc
    OOB Information for test2-abc.net.aol.com
    telnet ts-abc.oob.aol.com 1234
    Connecting you now...
    Trying 10.302.134.584...
    Connected to test2-abc.net.aol.com
    Escape character is '^]'.


    User Access Verification

    Username:

.. _gorc-doc:

Executing commands upon login
-----------------------------

You may create a ``.gorc`` file in your home directory, in which you may
specify commands to be executed upon login to a device. The commands are
specified by the vendor name. Here is an example::

    ; .gorc - Example file to show how .gorc would work

    [init_commands]
    ; Specify the commands you would like run upon login for each vendor name. The
    ; vendor name must match the one found in the CMDB for the manufacturer of the
    ; hardware. Currently these are:
    ;
    ;     A10: a10
    ;  Arista: arista
    ; Brocade: brocade
    ;   Cisco: cisco
    ;  Citrix: citrix
    ;    Dell: dell
    ; Foundry: foundry
    ; Juniper: juniper
    ;
    ; Format:
    ;
    ; vendor:
    ;     command1
    ;     command2
    ;
    juniper:
        request system reboot
        set cli timestamp
        monitor start messages
        show system users

    cisco:
        term mon
        who

    arista:
        python-shell

    foundry:
        show clock

    brocade:
        show clock

(You may also find this file at ``conf/gorc.example`` within the Trigger source
tree.)

Notice for **Juniper** one of the commands specified is ``request system
reboot``. This is bad! But don't worry, only a very limited subset of root
commands are allowed to be specified within the ``.gorc``, and these are::

    get
    monitor
    ping
    set
    show
    term
    terminal
    traceroute
    who
    whoami

Any root commands not permitted will be filtered out prior to passing them
along to the device.

Here is an example of what happens when you connect to a ``Juniper`` device
with the specified commands in the sample ``.gorc`` file displayed above::

    % gong test1-abc
    Connecting to test1-abc.net.aol.com.  Use ^X to exit.

    Fetching credentials from /home/jathan/.tacacsrc
    --- JUNOS 10.0S8.2 built 2010-09-07 19:55:32 UTC
    jathan@test1-abc> set cli timestamp
    Mar 28 23:05:38
    CLI timestamp set to: %b %d %T

    jathan@test1-abc> monitor start messages

    jathan@test1-abc> show system users
    Jun 28 23:05:39
    11:05PM  up 365 days, 13:44, 1 user, load averages: 0.09, 0.06, 0.02
    USER     TTY      FROM                              LOGIN@  IDLE WHAT
    jathan   p0       awesome.win.aol.com              11:05PM     - -cli (cli)

    jathan@test1-abc>
