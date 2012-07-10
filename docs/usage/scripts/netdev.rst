==================================
netdev - CLI search for NetDevices
==================================

.. contents::
    :local:
    :depth: 2

About
=====

**netdev** is a command-line search interface for :class:`~trigger.netdevices.NetDevices` metadata.

Usage
=====

Here is the usage output::

    % netdev
    Usage: netdev [options]

    Command-line search interface for 'NetDevices' metdata.

    Options:
      --version             show program's version number and exit
      -h, --help            show this help message and exit
      -a, --acls            Search will return acls instead of devices.
      -l <DEVICE>, --list=<DEVICE>
                            List all information for individual DEVICE
      -s, --search          Perform a search based on matching criteria
      -L <LOCATION>, --location=<LOCATION>
                            For use with -s:  Match on site location.
      -n <NODENAME>, --nodename=<NODENAME>
                            For use with -s:  Match on full or partial nodeName.
                            NO REGEXP.
      -t <TYPE>, --type=<TYPE>
                            For use with -s:  Match on deviceType.  Must be
                            FIREWALL, ROUTER, or SWITCH.
      -o <OWNING TEAM NAME>, --owning-team=<OWNING TEAM NAME>
                            For use with -s:  Match on Owning Team (owningTeam).
      -O <ONCALL TEAM NAME>, --oncall-team=<ONCALL TEAM NAME>
                            For use with -s:  Match on Oncall Team (onCallName).
      -C <OWNING ORG>, --owning-org=<OWNING ORG>
                            For use with -s:  Match on cost center Owning Org.
                            (owner).
      -v <VENDOR>, --vendor=<VENDOR>
                            For use with -s:  Match on canonical vendor name.
      -m <MANUFACTURER>, --manufacturer=<MANUFACTURER>
                            For use with -s:  Match on manufacturer.
      -b <BUDGET CODE>, --budget-code=<BUDGET CODE>
                            For use with -s:  Match on budget code
      -B <BUDGET NAME>, --budget-name=<BUDGET NAME>
                            For use with -s:  Match on budget name
      -k <MAKE>, --make=<MAKE>
                            For use with -s:  Match on make.
      -M <MODEL>, --model=<MODEL>
                            For use with -s:  Match on model.
      -N, --nonprod         Look for production and non-production devices.


Examples
========

Displaying an individual device
-------------------------------

You may use the ``-l`` option to list an individual device::

    % netdev -l test1-abc

            Hostname:          test1-abc.net.aol.com
            Owning Org.:       12345678 - Network Engineering
            Owning Team:       Data Center
            OnCall Team:       Data Center

            Vendor:            Juniper (JUNIPER)
            Make:              M40 INTERNET BACKBONE ROUTER
            Model:             M40-B-AC
            Type:              ROUTER
            Location:          LAB CR10 16ZZ

            Project:           Test Lab
            Serial:            987654321
            Asset Tag:         0000012345
            Budget Code:       1234578 (Data Center)

            Admin Status:      PRODUCTION
            Lifecycle Status:  INSTALLED
            Operation Status:  MONITORED
            Last Updated:      2010-07-19 19:56:32.0

Partial names are also ok::

    % netdev -l test1
    3 possible matches found for 'test1':
     [ 1] test1-abc.net.aol.com
     [ 2] test1-def.net.aol.com
     [ 3] test1-xyz.net.aol.com
     [ 0] Exit

    Enter a device number:

Searching by metadata
---------------------

To search you must specify the ``-s`` flag. All subsequent options are used as search terms. Each of the supported options coincides with attributes found on :class:`~trigger.netdevices.NetDevice` objects.

You must provide at least one optional field or this happens::

    % netdev -s
    netdev: error: -s needs at least one other option, excluding -l.

Search for all Juniper switches in site "BBQ"::

    % netdev -s -t switch -v juniper -L bbq

All search arguments accept partial matches and are case-INsensitive, so this::

    % netdev -s --manufacturer='CISCO SYSTEMS' --location=BBQ

Is equivalent to this::

    % netdev -s --manufacturer=cisco --location=bbq

You can't mix ``-l`` (list) and ``-s`` (search) because they contradict each other::

    % netdev -s -l -n test1
    Usage: netdev [options]

    netdev: error: -l and -s cannot be used together
