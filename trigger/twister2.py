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
from twisted.conch.ssh.common import NS
from twisted.conch.ssh.channel import SSHChannel
from twisted.conch.endpoints import SSHCommandClientEndpoint, _NewConnectionHelper, _CommandTransport, TCP4ClientEndpoint, connectProtocol
from twisted.conch.ssh.connection import SSHConnection
from twisted.conch import telnet
from twisted.internet import defer, protocol, reactor, stdio
from twisted.protocols.policies import TimeoutMixin
from twisted.python import log
from twisted.python.usage import Options
from xml.etree.ElementTree import (Element, ElementTree, XMLTreeBuilder)

from trigger.conf import settings
from trigger import tacacsrc, exceptions
from trigger.twister import is_awaiting_confirmation, has_ioslike_error
from trigger.utils import network, cli


class SSHSessionAddress(object):
    def __init__(self, server, username, command):
        self.server = server
        self.username = username
        self.command = command


class _TriggerShellChannel(SSHChannel):
    name = b'session'

    def __init__(self, creator, protocolFactory, commandConnected, commands,
                incremental, with_errors, timeout, command_interval):
        SSHChannel.__init__(self)
        self._creator = creator
        self._protocolFactory = protocolFactory
        self._commandConnected = commandConnected
        self.commands = commands
        self.incremental = incremental
        self.with_errors = with_errors
        self.timeout = timeout
        self.command_interval = command_interval
        self._reason = None

    def openFailed(self, reason):
	"""
	"""
	self._commandConnected.errback(reason)


    def channelOpen(self, ignored):
	"""
	"""
        pr = session.packRequest_pty_req(os.environ['TERM'],
                                         self._get_window_size(), '')

        self.conn.sendRequest(self, 'pty-req', pr)

	command = self.conn.sendRequest(
	    self, 'shell', '', wantReply=True)
        signal.signal(signal.SIGWINCH, self._window_resized)
	command.addCallbacks(self._execSuccess, self._execFailure)

    def _window_resized(self, *args):
        """Triggered when the terminal is rezied."""
        win_size = self._get_window_size()
        new_size = win_size[1], win_size[0], win_size[2], win_size[3]
        self.conn.sendRequest(self, 'window-change',
                              struct.pack('!4L', *new_size))

    def _get_window_size(self):
        """Measure the terminal."""
        stdin_fileno = sys.stdin.fileno()
        winsz = fcntl.ioctl(stdin_fileno, tty.TIOCGWINSZ, '12345678')
        return struct.unpack('4H', winsz)

    def _execFailure(self, reason):
	"""
	"""
	self._commandConnected.errback(reason)


    def _execSuccess(self, ignored):
	"""
	"""
	self._protocol = self._protocolFactory.buildProtocol(
                SSHSessionAddress(
                    self.conn.transport.transport.getPeer(),
                    self.conn.transport.creator.username,
                ''))
        self._bind_protocol_data()
        self._protocol.makeConnection(self)
	self._commandConnected.callback(self._protocol)

    def _bind_protocol_data(self):
        self._protocol.device = self.conn.transport.creator.hostname or None
        self._protocol.commands = self.commands or None
        self._protocol.commanditer = iter(self.commands) or None
        self._protocol.incremental = self.incremental or None
        self._protocol.with_errors = self.with_errors or None
        self._protocol.timeout = self.timeout or None
        self._protocol.command_interval = self.command_interval or None

    def dataReceived(self, data):
        self._protocol.dataReceived(data)
        SSHChannel.dataReceived(self, data)


class _TriggerSessionTransport(_CommandTransport):
    def verifyHostKey(self, hostKey, fingerprint):
        hostname = self.creator.hostname
        ip = self.transport.getPeer().host
 
        self._state = b'SECURING'
        # d = self.creator.knownHosts.verifyHostKey(
            # self.creator.ui, hostname, ip, Key.fromString(hostKey))
        # d.addErrback(self._saveHostKeyFailure)
        return defer.succeed(1)



class _NewTriggerConnectionHelperBase(_NewConnectionHelper):
    """
    Return object used for establishing an async session rather than executing a single command.
    """
    def __init__(self, reactor, hostname, port, username, keys, password,
            agentEndpoint, knownHosts, ui):
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

    def secureConnection(self):
         protocol = _TriggerSessionTransport(self)
         ready = protocol.connectionReady
 
         sshClient = TCP4ClientEndpoint(self.reactor, self.hostname, self.port)
 
         d = connectProtocol(sshClient, protocol)
         d.addCallback(lambda ignored: ready)
         return d


class TriggerSSHShellClientEndpointBase(SSHCommandClientEndpoint):
    """
    Base class for SSH endpoints.

    Subclass me when you want to create a new ssh client.
    """
    @classmethod
    def newConnection(cls, reactor, username, hostname, port=None,
            keys=None, password=None, agentEndpoint=None, knownHosts=None, ui=None):

        helper = _NewTriggerConnectionHelperBase(
                reactor, hostname, port, username, keys, password,
                agentEndpoint, knownHosts, ui)
        return cls(helper)


    def __init__(self, creator):
        self._creator = creator

    def _executeCommand(self, connection, protocolFactory, commands,
            incremental, with_errors, timeout, command_interval):
        commandConnected = defer.Deferred()
        def disconnectOnFailure(passthrough):
            # Close the connection immediately in case of cancellation, since
            # that implies user wants it gone immediately (e.g. a timeout):
            immediate =  passthrough.check(CancelledError)
            self._creator.cleanupConnection(connection, immediate)
            return passthrough
        commandConnected.addErrback(disconnectOnFailure)

        channel = _TriggerShellChannel(
                self._creator, protocolFactory, commandConnected, commands,
                incremental, with_errors, timeout, command_interval)
        connection.openChannel(channel)
        self.connected = True
        return commandConnected

    def connect(self, factory, commands, incremental=None,
            with_errors=None, timeout=0, command_interval=10):
        d = self._creator.secureConnection()
        d.addCallback(self._executeCommand, factory, commands,
                incremental, with_errors, timeout, command_interval)
        return d


class IoslikeSendExpect(protocol.Protocol, TimeoutMixin):
    """
    Action for use with TriggerTelnet as a state machine.

    Take a list of commands, and send them to the device until we run out or
    one errors. Wait for a prompt after each.
    """
    # def __init__(self, device, commands, incremental=None, with_errors=False,
                 # timeout=None, command_interval=0):
    def __init__(self):
        # self.device = self.transport.hostname
        # self._commands = self.transport.commands
        # self.commanditer = iter(_commands)
        # self.incremental = self.transport.incremental
        # self.with_errors = self.transport.with_errors
        # self.timeout = self.transport.timeout
        # self.command_interval = self.transport.command_interval
        self.prompt = re.compile('R1#')
        # self.prompt = re.compile(settings.IOSLIKE_PROMPT_PAT)
        # log.msg('[%s] My initialize commands: %s' % (self.device,
                                                     # 'some shit'))
        self.initialized = True


    def connectionMade(self):
        """Do this when we connect."""
        self.finished = defer.Deferred()
        self.setTimeout(self.timeout)
        self.results = self.factory.results = []
        self.data = ''
        log.msg('[%s] connectionMade, data: %r' % (self.device, self.data))
        self._send_next()


    def connectionLost(self, reason):
        self.finished.callback(None)


        # Don't call _send_next, since we expect to see a prompt, which
        # will kick off initialization.

    def dataReceived(self, bytes):
        """Do this when we get data."""
        log.msg('[%s] BYTES: %r' % (self.device, bytes))
        self.data += bytes

        # See if the prompt matches, and if it doesn't, see if it is waiting
        # for more input (like a [y/n]) prompt), and continue, otherwise return
        # None
        m = self.prompt.search(self.data)
        if not m:
            # If the prompt confirms set the index to the matched bytes,
            if is_awaiting_confirmation(self.data):
                log.msg('[%s] Got confirmation prompt: %r' % (self.device,
                                                              self.data))
                prompt_idx = self.data.find(bytes)
            else:
                return None
        else:
            # Or just use the matched regex object...
            prompt_idx = m.start()

        result = self.data[:prompt_idx]
        # Trim off the echoed-back command.  This should *not* be necessary
        # since the telnet session is in WONT ECHO.  This is confirmed with
        # a packet trace, and running self.transport.dont(ECHO) from
        # connectionMade() returns an AlreadyDisabled error.  What's up?
        log.msg('[%s] result BEFORE: %r' % (self.device, result))
        result = result[result.find('\n')+1:]
        log.msg('[%s] result AFTER: %r' % (self.device, result))

        if self.initialized:
            self.results.append(result)

        if has_ioslike_error(result) and not self.with_errors:
            log.msg('[%s] Command failed: %r' % (self.device, result))
            self.factory.err = exceptions.IoslikeCommandFailure(result)
            self.transport.loseConnection()
        else:
            if self.command_interval:
                log.msg('[%s] Waiting %s seconds before sending next command' %
                        (self.device, self.command_interval))
            reactor.callLater(self.command_interval, self._send_next)

    def _send_next(self):
        """Send the next command in the stack."""
        self.data = ''
        self.resetTimeout()

        if not self.initialized:
            log.msg('[%s] Not initialized, sending startup commands' %
                    self.device)
            if self.startup_commands:
                next_init = self.startup_commands.pop(0)
                log.msg('[%s] Sending initialize command: %r' % (self.device,
                                                                 next_init))
                self.transport.write(next_init.strip() + self.device.delimiter)
                return None
            else:
                log.msg('[%s] Successfully initialized for command execution' %
                        self.device)
                self.initialized = True

        if self.incremental:
            self.incremental(self.results)

        try:
            next_command = self.commanditer.next()
        except StopIteration:
            log.msg('[%s] No more commands to send, disconnecting...' %
                    self.device)
            self.transport.loseConnection()
            return None

        if next_command is None:
            self.results.append(None)
            self._send_next()
        else:
            log.msg('[%s] Sending command %r' % (self.device, next_command))
            self.transport.write(next_command + '\n')

    def timeoutConnection(self):
        """Do this when we timeout."""
        log.msg('[%s] Timed out while sending commands' % self.device)
        self.factory.err = exceptions.CommandTimeout('Timed out while '
                                                     'sending commands')
        self.transport.loseConnection()
