# -*- coding: utf-8 -*-

"""
Login and basic command-line interaction support using the Twisted asynchronous
I/O framework. The Trigger Twister is just like the Mersenne Twister, except
not at all.
"""

import copy
import fcntl
import os
import re
import signal
import socket
import struct
import sys
import tty
from twisted.conch.client.default import SSHUserAuthClient
from twisted.conch.ssh import channel, common, session, transport
from twisted.conch.endpoints import SSHCommandClientEndpoint, _NewConnectionHelper
from twisted.conch.ssh.connection import SSHConnection
from twisted.conch import telnet
from twisted.internet import defer, protocol, reactor, stdio
from twisted.protocols.policies import TimeoutMixin
from twisted.python import log
from twisted.python.usage import Options
from xml.etree.ElementTree import (Element, ElementTree, XMLTreeBuilder)

from trigger.conf import settings
from trigger import tacacsrc, exceptions
from trigger.utils import network, cli


__author__ = 'Thomas Cuthbert, Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan@gmail.com'
__copyright__ = 'Copyright 2006-2013, AOL Inc.; 2013 Salesforce.com.; 2016 Dropbox'
__version__ = '1.0.0'


class _NewTriggerConnectionHelperBase(_NewConnectionHelper):
    """
    Return object used for establishing an async session rather than executing a single command.
    """
    def __init__(self, reactor, hostname, port, username, keys,
            password, agentEndpoint, knownHosts, ui):
            self.reactor = reactor
            self.hostname = hostname
            self.port = port
            self.username = username
            self.keys = keys
            self.password = password
            self.agentEndpoint = agentEndpoint
            if knownHosts is None:
                knownHosts = self._knownHosts()
            self.knownHosts = knownHosts
            self.ui = ui




class TriggerSSHShellClientEndpointBase(SSHCommandClientEndpoint):
    """
    Base class for SSH endpoints.

    Subclass me when you want to create a new ssh client.
    """
    @classmethod
    def newConnection(cls, reactor, username, hostname, port=None,
            keys=None, password=None, agentEndpoint=None,
            knownHosts=None, ui=None):

        helper = _NewTriggerConnectionHelperBase(
                reactor, hostname, port, username, keys, password,
                agentEndpoint, knownHosts, ui)
        return cls(helper)


    def __init__(self, creator):
        self._creator = creator
        self._command = None
