#!/usr/bin/env python

import re
from datetime import datetime


class Router(object):
    showCommands = ['show run | i ip access-list', 'show ver']

    def __init__(self, name):
        self.name = name
        self.acls = []
        self.commands = []
        self.normalizeRequired = False
        self.version = None
        self.results = {}
        self.commando = None
        self.lastAccess = None

    def validate(self):
        """
        Updates the time that the device was last accessed and runs validation
        scripts to confirm the device state.
        """
        self.lastAccess = datetime.now()
        self.validateSystem()
        self.validateAcl()

    def validateSystem(self):
        """
        Valiated system level information for the device
        """
        for line in self.results["show ver"].splitlines():
            line = line.strip()
            m = re.search("^Cisco IOS Software.*Version (\S+), ", line)
            if m is not None:
                self.version = m.group(1)

    def validateAcl(self):
        """
        Validated ACLs on the device
        """
        self.acls = []
        for line in self.results["show run | i ip access-list"].splitlines():
            line = line.strip()
            m = re.search("ip access-list \S+ (\S+)", line)
            if m is not None:
                self.acls.append(m.group(1))

    def normalize(self):
        """
        Processes validation results and prepares commands that are required
        to normalize the device configuration
        """
        self.commands = []
        self.normalizeRequired = False
        if "trigger-test-1" not in self.acls:
            self.normalizeRequired = True
            self.commands += [
                "ip access-list standard trigger-test-1",
                "permit 1.1.1.1"
            ]
            print "{}: Will normalized trigger-test acl on device".format(
                self.name
            )

        pre_commands = ["conf t"]
        post_commands = ["end", "write mem"]
        self.commands = pre_commands+self.commands+post_commands
