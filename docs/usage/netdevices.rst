=======================
Working with NetDevices
=======================

:class:`~trigger.netdevices.NetDevices` is the core of Trigger's device interaction. Anything that
communicates with devices relies on the metadata stored within :class:`~trigger.netdevices.NetDevice`
objects.

netdevices.xml
==============

NetDevices reads in your ``netdevices.xml`` file that should be a dump of
relevant metadata fields from your CMDB. If you don't have a CMDB, then
you're going to have to populate this file manually. But you're a Python
programmer, right? So you can come up with something spiffy!

Here is what the ``netdevices.xml`` file bundled with the Trigger source
code looks like:

.. code-block:: xml

    <?xml version="1.0" encoding="UTF-8"?>
    <!-- Dummy version of netdevices.xml, with just one real entry modelded from the real file -->
    <NetDevices>
        <device nodeName="test1-abc.net.aol.com">
            <adminStatus>PRODUCTION</adminStatus>
            <assetID>0000012345</assetID>
            <authMethod>tacacs</authMethod>
            <barcode>0101010101</barcode>
            <budgetCode>1234578</budgetCode>
            <budgetName>Data Center</budgetName>
            <coordinate>16ZZ</coordinate>
            <deviceType>ROUTER</deviceType>
            <enablePW>boguspassword</enablePW>
            <lastUpdate>2010-07-19 19:56:32.0</lastUpdate>
            <layer2>1</layer2>
            <layer3>1</layer3>
            <layer4>1</layer4>
            <lifecycleStatus>INSTALLED</lifecycleStatus>
            <loginPW></loginPW>
            <make>M40 INTERNET BACKBONE ROUTER</make>
            <manufacturer>JUNIPER</manufacturer>
            <model>M40-B-AC</model>
            <nodeName>test1-abc.net.aol.com</nodeName>
            <onCallEmail>nobody@aol.net</onCallEmail>
            <onCallID>17</onCallID>
            <onCallName>Data Center</onCallName>
            <owningTeam>Data Center</owningTeam>
            <OOBTerminalServerConnector>C</OOBTerminalServerConnector>
            <OOBTerminalServerFQDN>ts1.oob.aol.com</OOBTerminalServerFQDN>
            <OOBTerminalServerNodeName>ts1</OOBTerminalServerNodeName>
            <OOBTerminalServerPort>5</OOBTerminalServerPort>
            <OOBTerminalServerTCPPort>5005</OOBTerminalServerTCPPort>
            <operationStatus>MONITORED</operationStatus>
            <owner>12345678 - Network Engineering</owner>
            <projectName>Test Lab</projectName>
            <room>CR10</room>
            <serialNumber>987654321</serialNumber>
            <site>LAB</site>
        </device>
        ...
    </NetDevices>

We plan to add support for different input sources including JSON, Sqlite, or 
"other" in the near future, but for now this is it.

By default the location of ``netdevices.xml`` can be specified one of two ways:

    1. Specifing the path in the ``NETDEVICESXML_FILE`` environment variable, or;
    2. modifying the value of of ``settings.NETDEVICESXML_FILE``.

Getting Started
===============

First things first, you must instantiate NetDevices.  It has three things it
requires before you can properly do this:

    1. The ``netdevices.xml`` file must be readable and must properly
       parse (see above); 
    2. An instance of Redis.
    3. The path to ``autoacl.py`` must be valid, and must properly parse.

How it works
------------

The NetDevices object itself is an immutable, dictionary-like Singleton_ object.
If you don't know what a Singleton is, it means that the actual there can only
really only be one instance in any program. The actual instance object itself an
instance of the inner :class:`~trigger.netdevices.NetDevices._actual` class which
is stored in the module object as ``NetDevices._Singleton``. This is done as a
performance boost because many Trigger components require a NetDevices instance,
and if we had to keep creating new ones, we'd be waiting forever each time one
had to parse ``netdevices.xml`` all over again.

Upon startup, each ``<device>`` element found within ``netdevices.xml`` is
used to create a ``NetDevice`` object.  This object pulls in ACL associations
from AclsDB.

.. _Singleton: http://en.wikipedia.org/wiki/Singleton_pattern

The Singleton Pattern
~~~~~~~~~~~~~~~~~~~~~

The NetDevices module object has a ``_Singleton`` attribute that defaults to ``None``.
Upon creating an instance, this is populated with the ``NetDevices._actual`` instance::

    >>> nd = NetDevices()
    >>> nd._Singleton
    <trigger.netdevices._actual object at 0x2ae3dcf48710>
    >>> NetDevices._Singleton
    <trigger.netdevices._actual object at 0x2ae3dcf48710>

This is how new instances are prevented. Whenever you create a new reference by
instantiating NetDevices again, what you are really doing is creating a reference
to ``NetDevices._Singleton``::

    >>> other_nd = NetDevices()
    >>> other_nd._Singleton
    <trigger.netdevices._actual object at 0x2ae3dcf48710>
    >>> nd._Singleton is other_nd._Singleton
    True

The only time this would be an issue is if you needed to change the actual contents 
of your object (such as when debugging ``netdevices.xml`` or passing 
``production_only=False``). If you need to do this, set the value to ``None``::

    >>> NetDevices._Singleton = None

Then the next call to ``NetDevices()`` will start from scratch. Keep in mind
because of this pattern it is not easy to have more than one instance (there are
ways but we're not going to list them here!). All existing instances will
inherit the value of ``NetDevices._Singleton``::

    >>> third_nd = NetDevices(production_only=False)
    >>> third_nd._Singleton
    <trigger.netdevices._actual object at 0x2ae3dcf506d0>
    >>> nd._Singleton
    <trigger.netdevices._actual object at 0x2ae3dcf506d0>
    >>> third_nd._Singleton is nd._Singleton
    True
 
Instantiating NetDevices
========================

Throughout the Trigger code, the convention when instantiating and referencing a
NetDevices instance, is to assign it to the variable ``nd``.  All examples will
use this, so keep that in mind::

    >>> from trigger.netdevices import NetDevices
    >>> nd = NetDevices()
    >>> len(nd)
    3

By default, this only includes any devices for which ``adminStatus`` (aka 
administrative status) is ``PRODUCTION``. This means that the device is used
in your production environment. If you would like you get all devices regardless
of ``adminStatus``, you must pass ``production_only=False`` to the constructor::

    >>> from trigger.netdevices import NetDevices
    >>> nd = NetDevices(production_only=False)
    >>> len(nd)
    4

The included sample ``netdevices.xml`` contains one device that is marked as
``NON-PRODUCTION``.

What's in a NetDevice?
======================

A :class:`~trigger.netdevices.NetDevice` object has a number of attributes you can use creatively to correlate
or identify them::

    >>> dev = nd.find('test1-abc')
    >>> dev
    <NetDevice: test1-abc.net.aol.com>

Printing it displays the hostname::

    >>> print dev
    test1-abc.net.aol.com

You can dump the values::

    >>> dev.dump()

            Hostname:          test1-abc.net.aol.com
            Owning Org.:       12345678 - Network Engineering
            Owning Team:       Data Center
            OnCall Team:       Data Center

            Manufacturer:      JUNIPER
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

You can reference them as attributes::

    >>> dev.nodeName, dev.manufacturer, dev.deviceType
    ('test1-abc.net.aol.com', 'JUNIPER', 'ROUTER')

There are some special methods to perform identity tests::

    >>> dev.is_router(), dev.is_switch(), dev.is_firewall()
    (True, False, False)
    
You can view the ACLs assigned to the device::

    >>> dev.explicit_acls
    set(['abc123'])
    >>> dev.implicit_acls
    set(['juniper-router.policer', 'juniper-router-protect'])
    >>> dev.acls
    set(['juniper-router.policer', 'juniper-router-protect', 'abc123'])

Or get the next time it's ok to make changes to this device (more on this later)::

    >>> dev.bounce.next_ok('green')
    datetime.datetime(2011, 7, 13, 9, 0, tzinfo=<UTC>)
    >>> print dev.bounce.status()
    red

Searching for devices
=====================

Like a dictionary
-----------------

Since the object is like a dictionary, you may reference devices as keys by their hostnames::

    >>> nd
    {'test2-abc.net.aol.com': <NetDevice: test2-abc.net.aol.com>,
     'test1-abc.net.aol.com': <NetDevice: test1-abc.net.aol.com>,
     'lab1-switch.net.aol.com': <NetDevice: lab1-switch.net.aol.com>,
     'fw1-xyz.net.aol.com': <NetDevice: fw1-xyz.net.aol.com>}
    >>> nd['test1-abc.net.aol.com']
    <NetDevice: test1-abc.net.aol.com>

You may also perform any other operations to iterate devices as you would with a dictionary (``.keys()``, ``.itervalues()``, etc.).

Special methods
---------------

There are a number of ways you can search for devices. In all cases, you are returned a list.

The simplest usage is just to list all devices::

    >>> nd.all()
    [<NetDevice: test2-abc.net.aol.com>, <NetDevice: test1-abc.net.aol.com>,
     <NetDevice: lab1-switch.net.aol.com>, <NetDevice: fw1-xyz.net.aol.com>]

Using ``all()`` is going to be very rare, as you're more likely to work with a subset of your
devices.

Find a device by its shortname (minus the domain)::

    >>> nd.find('test1-abc')
    <NetDevice: test1-abc.net.aol.com>

List devices by type (switches, routers, or firewalls)::

    >>> nd.list_routers()
    [<NetDevice: test2-abc.net.aol.com>, <NetDevice: test1-abc.net.aol.com>]
    >>> nd.list_switches()
    [<NetDevice: lab1-switch.net.aol.com>]
    >>> nd.list_firewalls()
    [<NetDevice: fw1-xyz.net.aol.com>]

Perform a case-sensitive search on any field (it defaults to ``nodeName``)::

    >>> nd.search('test')
    [<NetDevice: test2-abc.net.aol.com>, <NetDevice: test1-abc.net.aol.com>]
    >>> nd.search('test2')
    [<NetDevice: test2-abc.net.aol.com>]
    >>> nd.search('NON-PRODUCTION', 'adminStatus')
    [<NetDevice: test2-abc.net.aol.com>]

Or you could just roll your own list comprehension to do the same thing::

    >>> [d for d in nd.all() if d.adminStatus == 'NON-PRODUCTION']
    [<NetDevice: test2-abc.net.aol.com>]

Perform a case-INsenstive search on any number of fields as keyword arguments::

    >>> nd.match(oncallname='data center', adminstatus='non')
    [<NetDevice: test2-abc.net.aol.com>]
    >>> nd.match(manufacturer='netscreen')
    [<NetDevice: fw1-xyz.net.aol.com>]

Helper function
---------------

Another nifty tool within the module is :func:`~trigger.netdevices.device_match`, which returns a NetDevice object::

    >>> from trigger.netdevices import device_match
    >>> device_match('test')
    2 possible matches found for 'test':
     [ 1] test1-abc.net.aol.com
     [ 2] test2-abc.net.aol.com
     [ 0] Exit

    Enter a device number: 2
    <NetDevice: test2-abc.net.aol.com>

If there are multiple matches, it presents a prompt and lets you choose, otherwise it chooses for you::

    >>> device_match('fw')
    Matched 'fw1-xyz.net.aol.com'.
    <NetDevice: fw1-xyz.net.aol.com>