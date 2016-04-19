##############
Usage Examples
##############

To illustrate how Trigger works, here are some basic examples of leveraging the
API.

For these examples to work you must have already :doc:`installed
<installation>` and :doc:`configured <configuration>` Trigger, so if you
haven't already please do that first!

Simple Examples
===============

Working with metadata
---------------------

Get a count of all your devices::

    >>> from trigger.netdevices import NetDevices
    >>> nd = NetDevices()
    >>> len(nd)
    5539

(Whoa! That's a lot!) Let's look up a device.

::

    >>> dev = nd.find('edge1-abc')
    >>> dev.vendor, dev.deviceType
    (<Vendor: Juniper>, 'ROUTER')
    >>> dev.has_ssh()
    True

Get an interactive shell
------------------------

Since this device has SSH, let's connect to it::

    >>> dev = nd.find('edge1-abc')
    >>> dev.connect()
    Connecting to edge1-abc.net.aol.com.  Use ^X to exit.

    Fetching credentials from /home/jathan/.tacacsrc
    --- JUNOS 10.2S6.3 built 2011-01-22 20:06:27 UTC
    jathan@edge1-abc>

Work with access-lists
----------------------

Let's start with a simple Cisco ACL::

    >>> from trigger.acl import parse
    >>> aclobj = parse("""access-list 123 permit tcp any host 10.20.30.40 eq 80""")
    >>> aclobj.terms
    [<Term: None>]

And convert it to Juniper format::

    >>> aclobj.name_terms() # Juniper policy terms must have names
    >>> aclobj.terms
    [<Term: T1>]
    >>> print '\n'.join(aclobj.output(format='junos'))
    filter 123 {
        term T1 {
            from {
                destination-address {
                    10.20.30.40/32;
                }
                protocol tcp;
                destination-port 80;
            }
            then {
                accept;
            }
        }
    }

Cache your login credentials
----------------------------

Trigger will encrypt and store your credentials in a file called ``.tacacsrc``
in your home directory. We already had them cached in the previous examples, so
I removed it and then::

    >>> from trigger.tacacsrc import Tacacsrc
    >>> tcrc = Tacacsrc()
    /home/jathan/.tacacsrc not found, generating a new one!

    Updating credentials for device/realm 'tacacsrc'
    Username: jathan
    Password:
    Password (again):
    >>> tcrc.creds['aol']
    Credentials(username='jathan', password='boguspassword', realm='tacacsrc')

Passwords can be cached by realm. By default this realm is ``'aol'``, but you
can change that in the settings. Your credentials are encrypted and decrypted
using a shared key. A more secure experimental GPG-encrypted method is in the
works.

Login to a device using the ``gong`` script
-------------------------------------------

Trigger includes a simple tool for end-users to connect to devices called
``gong``. (It should be just ``go`` but we're in the future, so...)::

    $ gong foo1-cisco
    Connecting to foo1-cisco.net.aol.com.  Use ^X to exit.

    Fetching credentials from /home/jathan/.tacacsrc
    foo1-cisco#
    foo1-cisco#show clock
    20:52:05.777 UTC Sat Jun 23 2012
    foo1-cisco#

Partial hostnames are supported, too::

    $ gong foo1
    2 possible matches found for 'foo1':
    [ 1] foo1-abc.net.aol.com
    [ 2] foo1-xyz.net.aol.com
    [ 0] Exit

    Enter a device number: 2
    Connecting to foo1-xyz.net.aol.com.  Use ^X to exit.

    Fetching credentials from /home/jathan/.tacacsrc
    foo1-xyz#

Slightly Advanced Examples
==========================

Execute commands asynchronously using Twisted
---------------------------------------------

This is a little more advanced... so we saved it for last.

Trigger uses Twisted, which is a callback-based event loop. Wherever possible
Twisted's implementation details are abstracted away, but the power is there
for those who choose to wield it. Here's a super simplified example of how this
might be accomplished::

    from trigger.netdevices import NetDevices
    from twisted.internet import reactor

    nd = NetDevices()
    dev = nd.find('foo1-abc')

    def print_result(data):
        """Display results from a command"""
        print 'Result:', data

    def stop_reactor(data):
        """Stop the event loop"""
        print 'Stopping reactor'
        if reactor.running:
            reactor.stop()

    # Create an event chain that will execute a given list of commands on this
    # device
    async = dev.execute(['show clock'])

    # When we get results from the commands executed, call this
    async.addCallback(print_result)

    # Once we're out of commands, or we an encounter an error, call this
    async.addBoth(stop_reactor)

    # Start the event loop
    reactor.run()

Which outputs::

    Result: ['21:27:46.435 UTC Sat Jun 23 2012\n']
    Stopping reactor

Observe, however, that this only communicated with a single device.

Execute commands asynchronously using the Commando API
------------------------------------------------------

`~trigger.cmds.Commando` tries to hide Twisted's implementation details so you
don't have to deal with callbacks, while also implementing a worker pool so
that you may easily communicate with multiple devices in parallel.

This is a base class that is intended to be extended to perform the operations
you desire. Here is a basic example of how we might perform the same example
above using ``Commando`` instead, but also communicating with a second device
in parallel::

    from trigger.cmds import Commando

    class ShowClock(Commando):
        """Execute 'show clock' on a list of Cisco devices."""
        vendors = ['cisco']
        commands = ['show clock']

    if __name__ == '__main__':
        device_list = ['foo1-abc.net.aol.com', 'foo2-xyz.net.aol.com']
        showclock = ShowClock(devices=device_list)
        showclock.run() # Commando exposes this to start the event loop

        print '\nResults:'
        print showclock.results

Which outputs::

    Sending ['show clock'] to foo2-xyz.net.aol.com
    Sending ['show clock'] to foo1-abc.net.aol.com
    Received ['21:56:44.701 UTC Sat Jun 23 2012\n'] from foo2-xyz.net.aol.com
    Received ['21:56:44.704 UTC Sat Jun 23 2012\n'] from foo1-abc.net.aol.com

    Results:
    {
        'foo1-abc.net.aol.com': {
            'show clock': '21:56:44.704 UTC Sat Jun 23 2012\n'
        },
        'foo2-xyz.net.aol.com': {
            'show clock': '21:56:44.701 UTC Sat Jun 23 2012\n'
        }
    }

Get structured data back using the Commando API
-----------------------------------------------

`~trigger.cmds.Commando` The results from each worker are parsed through the TextFSM templating engine, if a matching template file exists within the `~trigger.settings.TEXTFSM_TEMPLATE_DIR` directory.

For this to work you must have an attribute on your netdevices model that specifies the network operating system, ie IOS, NXOS or JUNOS. This will be used to correlate the right template for a given device based on the naming convention used by the TextFSM templates.

Net Devices Object::

    {
        "adminStatus": "PRODUCTION", 
        "enablePW": "cisco", 
        "OOBTerminalServerTCPPort": "5005", 
        "assetID": "0000012345", 
        "OOBTerminalServerNodeName": "ts1", 
        "onCallEmail": "nobody@aol.net", 
        "onCallID": "17", 
        "OOBTerminalServerFQDN": "foo1-abc.net.aol.com",
        "owner": "12345678 - Network Engineering", 
        "OOBTerminalServerPort": "5", 
        "onCallName": "Data Center", 
        "nodeName": "foo1-abc.net.aol.com", 
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
        "loginPW": "cisco", 
        "lifecycleStatus": "INSTALLED", 
        "manufacturer": "CISCO", 
        "operatingSystem": "IOS", 
        "layer3": "1", 
        "layer2": "1", 
        "room": "CR10", 
        "layer4": "1", 
        "serialNumber": "987654321", 
        "owningTeam": "Data Center", 
        "coordinate": "16ZZ", 
        "model": "M40-B-AC", 
        "OOBTerminalServerConnector": "C"
    }

Template Naming Convention::

    {VENDOR}_{OS}_{COMMAND}.template


Template Directory Structure::

        $ tree vendor
        vendor
        └── ntc_templates
            ├── cisco_ios_show_clock.template
            ├── cisco_ios_show_inventory.template
            ├── cisco_ios_show_ip_int_brief.template
            ├── cisco_ios_show_version.template
            ├── cisco_nxos_show_clock.template
            ├── cisco_nxos_show_inventory.template
            ├── cisco_nxos_show_version.template

TextFSM Commando Implementation::

        class ShowMeTheMoney(Commando):
            """Execute the following on a list of Cisco devices:
                'show clock'
                'show version'
                'show ip int brief'
                'show inventory'
                'show run | in cisco'
            """
            vendors = ['cisco']
            commands = ['show clock', 'show version', 'show ip int brief', 'show inventory', 'show run | in cisco']

        if __name__ == '__main__':
            device_list = ['foo1-abc.net.aol.com'']
            showstuff = ShowMeTheMoney(devices=device_list)
            showstuff.run() # Commando exposes this to start the event loop

            print '\nResults:'
            pprint(showstuff.results)

            print '\nStruct Results:'
            pprint(showstuff.parsed_results)

Which outputs::

	Results:
	{'r1.demo.local': {'show clock': '*06:51:44.460 UTC Tue Mar 15 2016\r\n',
			   'show inventory': 'NAME: "Chassis", DESCR: "Cisco CSR1000V Chassis"\r\nPID: CSR1000V          , VID: V00, SN: 9G0T83AE5II\r\n\r\nNAME: "module R0", DESCR: "Cisco CSR1000V Route Processor"\r\nPID: CSR1000V          , VID: V00, SN: JAB1303001C\r\n\r\nNAME: "module F0", DESCR: "Cisco CSR1000V Embedded Services Processor"\r\nPID: CSR1000V          , VID:    , SN:            \r\n\r\n\r\n',
			   'show ip int brief': 'Interface              IP-Address      OK? Method Status                Protocol\r\nGigabitEthernet1       10.20.1.10      YES NVRAM  up                    up      \r\nGigabitEthernet2       unassigned      YES NVRAM  administratively down down    \r\nGigabitEthernet3       unassigned      YES NVRAM  administratively down down    \r\nGigabitEthernet4       unassigned      YES NVRAM  administratively down down    \r\n',
			   'show run | in cisco': 'username cisco secret 5 $1$zh1E$8GjiAf7YYDFPkLBYWMgpI0\r\n',
			   'show version': 'Cisco IOS XE Software, Version 03.12.00.S - Standard Support Release\r\nCisco IOS Software, CSR1000V Software (X86_64_LINUX_IOSD-UNIVERSALK9-M), Version 15.4(2)S, RELEASE SOFTWARE (fc2)\r\nTechnical Support: http://www.cisco.com/techsupport\r\nCopyright (c) 1986-2014 by Cisco Systems, Inc.\r\nCompiled Wed 26-Mar-14 21:09 by mcpre\r\n\r\n\r\nCisco IOS-XE software, Copyright (c) 2005-2014 by cisco Systems, Inc.\r\nAll rights reserved.  Certain components of Cisco IOS-XE software are\r\nlicensed under the GNU General Public License ("GPL") Version 2.0.  The\r\nsoftware code licensed under GPL Version 2.0 is free software that comes\r\nwith ABSOLUTELY NO WARRANTY.  You can redistribute and/or modify such\r\nGPL code under the terms of GPL Version 2.0.  For more details, see the\r\ndocumentation or "License Notice" file accompanying the IOS-XE software,\r\nor the applicable URL provided on the flyer accompanying the IOS-XE\r\nsoftware.\r\n\r\n\r\nROM: IOS-XE ROMMON\r\n\r\nR1 uptime is 1 minute\r\nUptime for this control processor is 3 minutes\r\nSystem returned to ROM by reload\r\nSystem image file is "bootflash:packages.conf"\r\nLast reload reason: <NULL>\r\n\r\n\r\n\r\nThis product contains cryptographic features and is subject to United\r\nStates and local country laws governing import, export, transfer and\r\nuse. Delivery of Cisco cryptographic products does not imply\r\nthird-party authority to import, export, distribute or use encryption.\r\nImporters, exporters, distributors and users are responsible for\r\ncompliance with U.S. and local country laws. By using this product you\r\nagree to comply with applicable laws and regulations. If you are unable\r\nto comply with U.S. and local laws, return this product immediately.\r\n\r\nA summary of U.S. laws governing Cisco cryptographic products may be found at:\r\nhttp://www.cisco.com/wwl/export/crypto/tool/stqrg.html\r\n\r\nIf you require further assistance please contact us by sending email to\r\nexport@cisco.com.\r\n\r\nLicense Level: limited\r\nLicense Type: Default. No valid license found.\r\nNext reload license Level: limited\r\n\r\ncisco CSR1000V (VXE) processor with 804580K/6147K bytes of memory.\r\nProcessor board ID 9G0T83AE5II\r\n4 Gigabit Ethernet interfaces\r\n32768K bytes of non-volatile configuration memory.\r\n2097152K bytes of physical memory.\r\n7774207K bytes of virtual hard disk at bootflash:.\r\n\r\nConfiguration register is 0x2102\r\n\r\n'}}


        Struct Results:
        {'foo1-abc.net.aol.com': {'show clock': {'day': ['10'],
                                          'dayweek': ['Thu'],
                                          'month': ['Mar'],
                                          'time': ['23:22:54.994'],
                                          'timezone': ['UTC'],
                                          'year': ['2016']},
                           'show inventory': {'descr': ['Cisco CSR1000V Chassis',
                                                        'Cisco CSR1000V Route Processor',
                                                        'Cisco CSR1000V Embedded Services Processor'],
                                              'name': ['Chassis',
                                                       'module R0',
                                                       'module F0'],
                                              'pid': ['CSR1000V',
                                                      'CSR1000V',
                                                      'CSR1000V'],
                                              'sn': ['9G0T83AE5II',
                                                     'JAB1303001C',
                                                     ''],
                                              'vid': ['V00', 'V00', '']},
                           'show ip int brief': {'intf': ['GigabitEthernet1',
                                                          'GigabitEthernet2',
                                                          'GigabitEthernet3',
                                                          'GigabitEthernet4'],
                                                 'ipaddr': ['10.20.1.10',
                                                            'unassigned',
                                                            'unassigned',
                                                            'unassigned'],
                                                 'proto': ['up',
                                                           'down',
                                                           'down',
                                                           'down'],
                                                 'status': ['up',
                                                            'administratively down',
                                                            'administratively down',
                                                            'administratively down']},
                           'show version': {'config_register': ['0x2102'],
                                            'hardware': ['CSR1000V'],
                                            'hostname': ['R1'],
                                            'running_image': ['packages.conf'],
                                            'serial': [''],
                                            'uptime': ['37 minutes'],
                                            'version': ['15.4(2)S']}}}
