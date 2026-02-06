#######################
Working with NetDevices
#######################

`~trigger.netdevices.NetDevices` is the core of Trigger's device interaction.
Anything that communicates with devices relies on the metadata stored within
`~trigger.netdevices.NetDevice` objects.

Your Source Data
================

Before you can work with device metadata, you must tell Trigger how and from
where to read it. You may either modify the values for these options within
``settings.py`` or you may specify the values as environment variables of the
same name as the configuration options.

Please see :doc:`configuration` for more information on how to do this. There
are two configuration options that facilitate this:

:setting:`NETDEVICES_SOURCE`
    A URL or file path from which the metadata may be obtained. This defaults to
    `/etc/trigger/netdevices.json`, but can be any URL with variables.

:setting:`NETDEVICES_LOADERS`
    (Advanced) A tuple of data loader classes, specified as strings. This is an
    advanced setting that you may use to create custom loaders if any of the
    default loaders do not meet your needs. The primary default loader is the
    `~trigger.netdevices.loaders.filesystem.JSONLoader`.

A Brief Overview
----------------

When you instantiate `~trigger.netdevices.NetDevices` the location specified
:setting:`NETDEVICES_SOURCE` is passed onto the :setting:`NETDEVICES_LOADERS`
to try to parse and return device metadata.

Using the loaders, you don't have to tell Trigger what the format of your
metadata source is. It tries to determine it automatically based on whether one
of the pre-defined loaders successfully returns data without throwing an error.

Anatomy of a Device
===================

Trigger's `~trigger.netdevices.NetDevice` objects represent everything Trigger
needs to know about each device under its care. These objects are pretty
complicated, but all you really need to know right now are the bare minimum set
of fields that Trigger needs to know about your devices. These fields are used
to control the behaviors and select the correct driver for each platform.

Field Values
------------

Field values are expected to be strings. They are normalized prior to
evaluation, so case-sensitivity can be left up to you based on how you choose
to manage your data in your environment.

You may also specify custom fields not used or required by Trigger that you may
use for your own purposes, such as writing custom utilities.

Minium Required Fields
----------------------

These are the bare minimum required fields for basic operations of Trigger on
most device platforms. Due to distinct differences across device platforms by
vendor, hardware, and operating system versions, not all device platforms can
be supported with the minimum felds.

.. important::
    Support for certain device platforms, such as the Cisco Nexus, require
    specifying other fields as detailed in the next section.

nodeName
    The device hostname or IP address. Trigger does not validate this value for
    you, so it must be able to be to be reconciled by the host system on which
    Trigger is running. You may also specify a port here by separating the
    hostname and port by a colon (e.g. ``hostname:2222``) . We'll cover that in
    more detail later.

manufacturer
    The representative name of the hardware vendor. This is also used to
    dynamically populate the ``vendor`` attribute on the device object. For
    Trigger's list of supported vendors, please see
    :setting:`SUPPORTED_VENDORS`.

adminStatus
    (Recommended) The administrative status of the device. One of ``PRODUCTION`` or
    ``NON-PRODUCTION``. By default, Trigger will only work with devices that
    are in ``PRODUCTION`` status. This is covered in more detail under
    :ref:`instantiating-netdevices`. If you do NOT specifiy ``adminStatus``,
    Trigger will fallback to the default value specified in
    :setting:`DEFAULT_ADMIN_STATUS`.

deviceType
    (Recommended) The type of device (e.g. router, switch, etc.). For the list
    of supported device types, please see :setting:`SUPPORTED_TYPES`. If you do
    NOT specify ``deviceType``, Trigger will fallback to the type specified in
    :setting:`FALLBACK_TYPE`.

For example the minimum required fields for a device using JSON might be:

.. code-block:: javascript

    {
        "nodeName": "n9k1",
        "deviceType": "SWITCH",
        "manufacturer": "CISCO",
        "model": "NEXUS",
        "adminStatus": "PRODUCTION"
    }

Common Fields
-------------

Some vendors, such as Cisco for example, have a wide array of hardware types
with many different operating systems. For this reason, not all devices can be
supported with just vendor and device type. To identify these platforms,
we also make use of the ``make`` and ``model`` fields.

The following fields are required for full support of all officially supported
vendor platforms.

make
    The device platform such as ``Cisco Nexus`` or just ``Nexus``.

model
    The specific device model as it appears on the network device, such as
    ``N9K`` or ``NEXUS 9000``.

Other Fields
------------

There are a ton of other default fields that Trigger utilizes for other
purposes.

Quick Start
===========

To get started quickly managing real devices, try this:

1. Create a :ref:`csv-format` file.
2. Tell Trigger where to find your file by setting the locatoin of the file in
   :setting:`NETDEVICES_SOURCE` in your ``settings.py``.

Importing from RANCID
---------------------

Do you have RANCID? Try using that instead! To learn more please visit the
section on working with the :ref:`rancid-format` format.

Supported Formats
=================

Trigger currently comes with loaders that support the following formats:

.. contents::
    :local:
    :depth: 1

Except when using CSV or RANCID as a data source, the contents of your source
data should be a dump of relevant metadata fields from your CMDB.

If you don't have a CMDB, then you're going to have to populate this file
manually.

.. _csv-format:

CSV
---

.. versionadded:: 1.3

This method is the most lightweight, but also the most limited. But it's a
great starting point!

The bare minimum config for CSV is a file populated comma-separated values,
each on their own line with ``hostname,vendor``. For example::

    test1-abc.net.aol.com,juniper
    test2-abc.net.aol.com,cisco

The most fields you may populate are the same as with the RANCID support.
Please see the explanation of the fields populated by the :ref:`RANCID format
<rancid-format>`. A "fully-populated" CSV file would look more like this::

    test1-abc.net.aol.com,juniper,up,router
    test2-abc.net.aol.com,juniper,up,router
    fw1-xyz.net.aol.com,netscreen,up,firewall
    lab1-switch.net.aol.com,foundry,up,switch

.. _xml-format:

XML
---

XML is the slowest method supported by Trigger, but it is currently the default
for legacy reasons. At some point we will switch JSON to the default.

Here is a sample what the ``netdevices.xml`` file bundled with the Trigger
source code looks like:

.. code-block:: xml

    <?xml version="1.0" encoding="UTF-8"?>
    <!-- Dummy version of netdevices.xml, with just one real entry modeled from the real file -->
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

Please see ``configs/netdevices.xml`` within the Trigger source distribution for a
full example.

.. _json-format:

JSON
----

JSON is the fastest method supported by Trigger. This is especially the case if
you utilize the optional C extension of  `simplejson
<http://pypi.python.org/pypi/simplejson>`. The file can be minified and does
not need to be indented.

Here is a sample of what the ``netdevices.json`` file bundled with the Trigger
source code looks like (pretty-printed for readabilty):

.. code-block:: javascript

    [
        {
            "adminStatus": "PRODUCTION",
            "enablePW": "boguspassword",
            "OOBTerminalServerTCPPort": "5005",
            "assetID": "0000012345",
            "OOBTerminalServerNodeName": "ts1",
            "onCallEmail": "nobody@aol.net",
            "onCallID": "17",
            "OOBTerminalServerFQDN": "ts1.oob.aol.com",
            "owner": "12345678 - Network Engineering",
            "OOBTerminalServerPort": "5",
            "onCallName": "Data Center",
            "nodeName": "test1-abc.net.aol.com",
            "make": "M40 INTERNET BACKBONE ROUTER",
            "budgetCode": "1234578",
            "budgetName": "Data Center",
            "operationStatus": "MONITORED",
            "deviceType": "ROUTER",
            "lastUpdate": "2010-07-19 19:56:32.0",
            "authMethod": "tacacs",
            "projectName": "Test Lab",
            "barcode": "0101010101",
            "site": "LAB",
            "loginPW": null,
            "lifecycleStatus": "INSTALLED",
            "manufacturer": "JUNIPER",
            "layer3": "1",
            "layer2": "1",
            "room": "CR10",
            "layer4": "1",
            "serialNumber": "987654321",
            "owningTeam": "Data Center",
            "coordinate": "16ZZ",
            "model": "M40-B-AC",
            "OOBTerminalServerConnector": "C"
        },
        ...
    ]

To use JSON, create your :setting:`NETDEVICES_SOURCE` file full of objects that
look like the one above.

Please see ``configs/netdevices.json`` within the Trigger source distribution for
a full example.

.. _rancid-format:

RANCID
------

If you've already got a RANCID instance in your environment, this is the
easiest method to get running. At this time, however, the metadata available
from RANCID is very limited and populates only the following fields for each
`~trigger.netdevices.Netdevice` object:

* nodeName
* manufacturer
* deviceType
* adminStatus

The support for RANCID comes in two forms: single or multiple instance.

Single instance is the default and expects to find the ``router.db`` file and
the ``configs`` directory in the root directory you specify.

Multiple instance will instead walk the root directory and expect to find
``router.db`` and ``configs`` in each subdirectory it finds. Multiple instance
can be toggled by seting the value of :setting:`RANCID_RECURSE_SUBDIRS` to
``True`` to your ``settings.py``.

To use RANCID as a data source, set the value of :setting:`NETDEVICES_SOURCE` in
``settings.py`` to the absolute path of location of of the root directory where
your RANCID data is stored.

.. note::

    Make sure that the value of :setting:`RANCID_RECURSE_SUBDIRS` matches the RANCID
    method you are using. This setting defaults to ``False``, so if you only
    have a single RANCID instance, there is no need to add it to your
    ``settings.py``.

Lastly, to illustrate what a `~trigger.netdevices.NetDevice` object that has
been populated by RANCID looks like, here is the output of ``.dump()``::


        Hostname:          test1-abc.net.aol.com
        Owning Org.:       None
        Owning Team:       None
        OnCall Team:       None

        Vendor:            Juniper (juniper)
        Make:              None
        Model:             None
        Type:              ROUTER
        Location:          None None None

        Project:           None
        Serial:            None
        Asset Tag:         None
        Budget Code:       None (None)

        Admin Status:      PRODUCTION
        Lifecycle Status:  None
        Operation Status:  None
        Last Updated:      None

Compare that to what a device dump looks like when fully populated from CMDB
metadata in :ref:`netdevice-info`. It's important to keep this in mind, because
if you want to do device associations using any of the unpopulated fields,
you're gonna have a bad time. This is subject to change as RANCID support
evolves, but this is the way it is for now.

.. _sqlite-format:

SQLite
------

SQLite is somewhere between JSON and XML as far as performance, but also comes
with the added benefit that support is built into Python, and you get a real
database file you can leverage in other ways outside of Trigger.

.. literalinclude:: ../../configs/netdevices.sql
    :language: sql

To use SQLite, create a database using the schema provided within Trigger
source distribution at ``configs/netdevices.sql``. You will need to populate the
database full of rows with the columns above and set
:setting:`NETDEVICES_SOURCE` the absolute path of the database file.

Developing with NetDevices
==========================

First things first, you must instantiate `~trigger.netdevices.NetDevices`.  It
has three things it requires before you can properly do this:

.. note::
    If you do not want to load ACL associations you may skip them by passing
    ``with_acls=False`` to `~trigger.netdevices.NetDevices` and then you only need
    to satisfy the first requirement. A this time it is not possible to
    globally disable ACL support, so this will only work for the purpose of
    this walkthrough or when you manually instantiate NetDevices objects.

1. The :setting:`NETDEVICES_SOURCE` file must be readable and must properly
   parse using one of the default loaders formats supported in
   :setting:`NETDEVICES_LOADERS` (see above);
2. An instance of Redis (you may skip this by passing ``with_acls=False``
   to the `~trigger.netdevices.NetDevices` constructor).
3. The path to ``autoacl.py`` must be valid, and must properly parse (you
   may skip this if you just want to ignore the warnings for now).

How it works
------------

The `~trigger.netdevices.NetDevices` object itself is an immutable,
dictionary-like Singleton_ object. If you don't know what a Singleton is, it
means that there can only be one instance of this object in any program. The
actual instance object itself an instance of the inner
:class:`~trigger.netdevices.NetDevices._actual` class which is stored in the
module object as ``NetDevices._Singleton``. This is done as a performance boost
because many Trigger components require a NetDevices instance, and if we had to
keep creating new ones, we'd be waiting each time one had to parse
:setting:`NETDEVICES_SOURCE` all over again.

Upon startup, each device object/element/row found within
:setting:`NETDEVICES_SOURCE` is used to create a
`~trigger.netdevices.NetDevice` object. This object pulls in ACL associations
from `~trigger.acl.db.AclsDB`.

.. _Singleton: http://en.wikipedia.org/wiki/Singleton_pattern

The Singleton Pattern
~~~~~~~~~~~~~~~~~~~~~

The NetDevices module object has a ``_Singleton`` attribute that defaults to
``None``. Upon creating an instance, this is populated with the
`~trigger.netdevices.NetDevices._actual` instance::

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
of your object (such as when debugging or passing ``production_only=False``).
If you need to do this, set the value to ``None``::

    >>> NetDevices._Singleton = None

Then the next call to `~trigger.netdevices.NetDevices()` will start from
scratch. Keep in mind because of this pattern it is not easy to have more than
one instance (there are ways but we're not going to list them here!). All
existing instances will inherit the value of ``NetDevices._Singleton``::

    >>> third_nd = NetDevices(production_only=False)
    >>> third_nd._Singleton
    <trigger.netdevices._actual object at 0x2ae3dcf506d0>
    >>> nd._Singleton
    <trigger.netdevices._actual object at 0x2ae3dcf506d0>
    >>> third_nd._Singleton is nd._Singleton
    True

.. _instantiating-netdevices:

Instantiating NetDevices
------------------------

Throughout the Trigger code, the convention when instantiating and referencing a
`~trigger.netdevices.NetDevices` instance, is to assign it to the variable
``nd``.  All examples will use this, so keep that in mind::

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

The included sample metadata files contains one device that is marked as
``NON-PRODUCTION``.

.. _netdevice-info:

What's in a NetDevice?
----------------------

A `~trigger.netdevices.NetDevice` object has a number of attributes you can use
creatively to correlate
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

You can reference them as attributes::

    >>> dev.nodeName, dev.vendor, dev.deviceType
    ('test1-abc.net.aol.com', <Vendor: Juniper>, 'ROUTER')

There are some special methods to perform identity tests::

    >>> dev.is_router(), dev.is_switch(), dev.is_firewall()
    (True, False, False)

You can view the ACLs assigned to the device:

.. note::
    If you have passed ``with_acls=False``, none of these attributes will be
    populated and will instead return an empty ``set()``).

::

    >>> dev.explicit_acls
    set(['abc123'])
    >>> dev.implicit_acls
    set(['juniper-router.policer', 'juniper-router-protect'])
    >>> dev.acls
    set(['juniper-router.policer', 'juniper-router-protect', 'abc123'])

Or get the next time it's ok to make changes to this device (more on this
later)::

    >>> dev.bounce.next_ok('green')
    datetime.datetime(2011, 7, 13, 9, 0, tzinfo=<UTC>)
    >>> print dev.bounce.status()
    red

Searching for devices
---------------------

Like a dictionary
~~~~~~~~~~~~~~~~~

Since the object is like a dictionary, you may reference devices as keys by
their hostnames::

    >>> nd
    {'test2-abc.net.aol.com': <NetDevice: test2-abc.net.aol.com>,
     'test1-abc.net.aol.com': <NetDevice: test1-abc.net.aol.com>,
     'lab1-switch.net.aol.com': <NetDevice: lab1-switch.net.aol.com>,
     'fw1-xyz.net.aol.com': <NetDevice: fw1-xyz.net.aol.com>}
    >>> nd['test1-abc.net.aol.com']
    <NetDevice: test1-abc.net.aol.com>

You may also perform any other operations to iterate devices as you would with
a dictionary (``.keys()``, ``.itervalues()``, etc.).

Special methods
~~~~~~~~~~~~~~~

There are a number of ways you can search for devices. In all cases, you are
returned a list.

The simplest usage is just to list all devices::

    >>> nd.all()
    [<NetDevice: test2-abc.net.aol.com>, <NetDevice: test1-abc.net.aol.com>,
     <NetDevice: lab1-switch.net.aol.com>, <NetDevice: fw1-xyz.net.aol.com>]

Using ``all()`` is going to be very rare, as you're more likely to work with a
subset of your
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
    >>> nd.match(vendor='netscreen')
    [<NetDevice: fw1-xyz.net.aol.com>]

Helper function
~~~~~~~~~~~~~~~

Another nifty tool within the module is `~trigger.netdevices.device_match`,
which returns a NetDevice object::

    >>> from trigger.netdevices import device_match
    >>> device_match('test')
    2 possible matches found for 'test':
     [ 1] test1-abc.net.aol.com
     [ 2] test2-abc.net.aol.com
     [ 0] Exit

    Enter a device number: 2
    <NetDevice: test2-abc.net.aol.com>

If there are multiple matches, it presents a prompt and lets you choose,
otherwise it chooses for you::

    >>> device_match('fw')
    Matched 'fw1-xyz.net.aol.com'.
    <NetDevice: fw1-xyz.net.aol.com>
