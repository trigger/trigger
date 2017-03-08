####################################
gnng - Display interface information
####################################

About
=====

**gnng** Fetches interface information from routing and firewall devices. This
includes network and IP information along with the inbound and outbound filters
that  may be applied to the interface. Skips un-numbered and disabled
interfaces by default. Works on Cisco, Foundry, Juniper, and NetScreen devices.

Usage
=====

Here is the usage output:

.. code-block:: bash

    $ gnng -h
    Usage: gnng [options] [routers]

    GetNets-NG  Fetches interface information from routing and firewall devices.
    This includes network and IP information along with the inbound and outbound
    filters that  may be applied to the interface. Skips un-numbered and disabled
    interfaces by default. Works on Cisco, Foundry, Juniper, and NetScreen
    devices.

    Options:
      -h, --help            show this help message and exit
      -a, --all             run on all devices
      -c, --csv             output the data in CSV format instead.
      -d, --include-disabled
                            include disabled interfaces.
      -u, --include-unnumbered
                            include un-numbered interfaces.
      -j JOBS, --jobs=JOBS  maximum simultaneous connections to maintain.
      -N, --nonprod         Look for production and non-production devices.
      -s SQLDB, --sqldb=SQLDB
                            output to SQLite DB
      --dotty               output connect-to information in dotty format.
      --filter-on-group=FILTER_ON_GROUP
                            Run on all devices owned by this group
      --filter-on-type=FILTER_ON_TYPE
                            Run on all devices with this device type

Examples
========

Displaying interfaces for a device
----------------------------------

To fetch interface information for a device, just provide its hostname as an argument:

.. code-block:: bash

    $ gnng test1-abc.net.aol.com
    DEVICE: test1-abc.net.aol.com
    Interface  | Addresses     | Subnets        | ACLs IN | ACLs OUT    | Description                                       
    -------------------------------------------------------------------------------------------
    fe-1/2/1.0 | 10.10.20.38   | 10.10.20.36/30 |         | count_all   | this is an interface 
               |               |                |         | test_filter |                                                   
    ge-1/1/0.0 | 1.2.148.246   | 1.2.148.244/30 |         | filterbad   | and so is this
    lo0.0      | 10.10.20.253  | 10.10.20.253   | protect |             |                                                   
               | 10.10.20.193  | 10.10.20.193   |         |             |                                                   

You may specify any number of device hostnames as arguments, or to fetch ALL
devices pass the ``-a`` flag.

The rest is fairly self-explanatory.
