import unittest
import os
import mock
from trigger.netdevices import NetDevices
from trigger.cmds import Commando
from trigger.utils.templates import *
from contextlib import contextmanager
from StringIO import StringIO
import cStringIO


# Constants
DEVICE_NAME = 'test1-abc.net.aol.com'
DEVICE2_NAME = 'test2-abc.net.aol.com'

try:
    import textfsm
except ImportError:
    print("""
    Woops, looks like you're missing the textfsm library.

    Try installing it like this::

        >>> pip install gtextfsm
    """)


cli_data = """*02:00:42.743 UTC Sat Feb 20 2016"""
big_cli_data = """Cisco IOS XE Software, Version 03.12.00.S - Standard Support Release
Cisco IOS Software, CSR1000V Software (X86_64_LINUX_IOSD-UNIVERSALK9-M), Version 15.4(2)S, RELEASE SOFTWARE (fc2)
Technical Support: http://www.cisco.com/techsupport
Copyright (c) 1986-2014 by Cisco Systems, Inc.
Compiled Wed 26-Mar-14 21:09 by mcpre


Cisco IOS-XE software, Copyright (c) 2005-2014 by cisco Systems, Inc.
All rights reserved.  Certain components of Cisco IOS-XE software are
licensed under the GNU General Public License ("GPL") Version 2.0.  The
software code licensed under GPL Version 2.0 is free software that comes
with ABSOLUTELY NO WARRANTY.  You can redistribute and/or modify such
GPL code under the terms of GPL Version 2.0.  For more details, see the
documentation or "License Notice" file accompanying the IOS-XE software,
or the applicable URL provided on the flyer accompanying the IOS-XE
software.


ROM: IOS-XE ROMMON

R1 uptime is 2 hours, 22 minutes
Uptime for this control processor is 2 hours, 23 minutes
System returned to ROM by reload
System image file is "bootflash:packages.conf"
Last reload reason: <NULL>



This product contains cryptographic features and is subject to United
States and local country laws governing import, export, transfer and
use. Delivery of Cisco cryptographic products does not imply
third-party authority to import, export, distribute or use encryption.
Importers, exporters, distributors and users are responsible for
compliance with U.S. and local country laws. By using this product you
agree to comply with applicable laws and regulations. If you are unable
to comply with U.S. and local laws, return this product immediately.

A summary of U.S. laws governing Cisco cryptographic products may be found at:
http://www.cisco.com/wwl/export/crypto/tool/stqrg.html

If you require further assistance please contact us by sending email to
export@cisco.com.

License Level: limited
License Type: Default. No valid license found.
Next reload license Level: limited

cisco CSR1000V (VXE) processor with 804580K/6147K bytes of memory.
Processor board ID 9G0T83AE5II
4 Gigabit Ethernet interfaces
32768K bytes of non-volatile configuration memory.
2097152K bytes of physical memory.
7774207K bytes of virtual hard disk at bootflash:.

Configuration register is 0x2102"""

text_fsm_data = """Value TIME (\d+:\d+:\d+\.\d+)
Value TIMEZONE (\w+)
Value DAYWEEK (\w+)
Value MONTH (\w+)
Value DAY (\d+)
Value YEAR (\d+)

Start
  ^[\*]?${TIME}\s${TIMEZONE}\s${DAYWEEK}\s${MONTH}\s${DAY}\s${YEAR} -> Record
"""
no_template_data = "username cisco"


def _reset_netdevices():
    """Reset the Singleton state of NetDevices class."""
    NetDevices._Singleton = None


class CheckTemplates(unittest.TestCase):
    """Test structured CLI object data."""

    def setUp(self):
        data = cStringIO.StringIO(text_fsm_data)
        self.re_table = textfsm.TextFSM(data)
        self.assertTrue(isinstance(self.re_table, textfsm.textfsm.TextFSM))

        self.nd = NetDevices()
        self.device = self.nd[DEVICE_NAME]
        self.device.vendor = "cisco"
        self.device.operatingSystem = "ios"

    def testTemplatePath(self):
        """Test that template path is correct."""
        t_path = get_template_path("show clock", dev_type="cisco_ios")
        self.failUnless("vendor/ntc_templates/cisco_ios_show_clock.template" in t_path)

    def testGetTextFsmObject(self):
        """Test that we get structured data back from cli output."""
        data = get_textfsm_object(self.re_table, cli_data)
        self.assertTrue(isinstance(data, dict))
        keys = ['dayweek', 'time', 'timezone', 'year', 'day', 'month']
        for key in keys:
            self.assertTrue(data.has_key(key))

    def testCommandoResultsGood(self):
        commands = ["show version"]
        commando = Commando(devices=[self.device.nodeName])
        data = commando.parse_template(results=[big_cli_data], device=self.device, commands=commands)
        self.assertTrue(len(data) > 0)
        self.assertTrue(isinstance(data, list))
        self.assertTrue(isinstance(data[0], str))
        self.assertTrue(isinstance(commando.parsed_results, dict))
        self.assertEquals(commando.parsed_results.popitem()[1]["show version"]["hardware"], ['CSR1000V'])

    def testCommandoResultsBad(self):
        commands = ["show run | in cisco"]
        commando = Commando(devices=[self.device.nodeName])
        data = commando.parse_template(results=[no_template_data], device=self.device, commands=commands)
        self.assertTrue(len(data) > 0)
        self.assertTrue(isinstance(data, list))
        self.assertTrue(isinstance(data[0], str))
        self.assertEquals(commando.parsed_results, {})

    def tearDown(self):
        _reset_netdevices()

if __name__ == "__main__":
    unittest.main()
