# -*- coding: utf-8 -*-

"""
Login and basic command-line interaction support using the Twisted asynchronous
I/O framework. The Trigger Twister is just like the Mersenne Twister, except
not at all.
"""

import fcntl
import os
import re
import signal
import struct
import sys
import tty
from copy import copy
from collections import deque
from crochet import wait_for, run_in_reactor, setup, EventLoop

setup()

from twisted.conch.ssh import session, common, transport
from twisted.conch.ssh.channel import SSHChannel
from twisted.conch.endpoints import (SSHCommandClientEndpoint,
                                     _NewConnectionHelper,
                                     _ExistingConnectionHelper,
                                     _CommandTransport, TCP4ClientEndpoint,
                                     connectProtocol,
                                     _UserAuth,
                                     _ConnectionReady)
from twisted.internet import defer, protocol, reactor, threads
from twisted.internet.defer import CancelledError
from twisted.internet.task import LoopingCall
from twisted.protocols.policies import TimeoutMixin
from twisted.python import log

from trigger.conf import settings
from trigger import tacacsrc, exceptions
from trigger.twister import is_awaiting_confirmation, has_ioslike_error, TriggerSSHUserAuth
from twisted.internet import reactor


@run_in_reactor
def generate_endpoint(device):
    """Generate Trigger endpoint for a given device.

    The purpose of this function is to generate endpoint clients for use by a `~trigger.netdevices.NetDevice` object.

    :param device: `~trigger.netdevices.NetDevice` object
    """
    creds = tacacsrc.get_device_password(device.nodeName)
    return TriggerSSHShellClientEndpointBase.newConnection(
        reactor, creds.username, device, password=creds.password
    )

class SSHSessionAddress(object):
    """This object represents an endpoint's session details.

    This object would typically be loaded as follows:

    :Example:
        >>> sess = SSHSessionAddress()
        >>> sess.server = "1.2.3.4"
        >>> sess.username = "cisco"
        >>> sess.command = ""
    
    We load command with a null string as Cisco device's typically do not support bash!
    """
    def __init__(self, server, username, command):
        self.server = server
        self.username = username
        self.command = command


class _TriggerShellChannel(SSHChannel):
    """This is the Trigger subclassed Channel object.
    """
    name = b'session'

    def __init__(self, creator, command, protocolFactory, commandConnected, incremental,
            with_errors, prompt_pattern, timeout, command_interval):
        SSHChannel.__init__(self)
        self._creator = creator
        self._protocolFactory = protocolFactory
        self._command = command
        self._commandConnected = commandConnected
        self.incremental = incremental
        self.with_errors = with_errors
        self.prompt = prompt_pattern
        self.timeout = timeout
        self.command_interval = command_interval
        self._reason = None

    def openFailed(self, reason):
        """Channel failed handler."""
        self._commandConnected.errback(reason)


    def channelOpen(self, ignored):
        """Channel opened handler.
        
        Once channel is opened, setup the terminal environment and signal
        endpoint to load the shell subsystem.
        """
        pr = session.packRequest_pty_req(os.environ['TERM'],
                                         self._get_window_size(), '')
        self.conn.sendRequest(self, 'pty-req', pr)

        command = self.conn.sendRequest(
            self, 'shell', '', wantReply=True)
        # signal.signal(signal.SIGWINCH, self._window_resized)
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
        """Callback for when the exec command fails.
        """
        self._commandConnected.errback(reason)


    def _execSuccess(self, ignored):
        """Callback for when the exec command succees.
        """
        self._protocol = self._protocolFactory.buildProtocol(
                SSHSessionAddress(
                    self.conn.transport.transport.getPeer(),
                    self.conn.transport.creator.username,
                    self._command
                    ))
        self._bind_protocol_data()
        self._protocol.makeConnection(self)
        self._commandConnected.callback(self._protocol)

    def _bind_protocol_data(self):
        """Helper method to bind protocol related attributes to the channel.
        """
        # This was a string before, now it's a NetDevice.
        self._protocol.device = self.conn.transport.creator.device or None

        # FIXME(jathan): Is this potentially non-thread-safe?
        self._protocol.startup_commands = copy(
            self._protocol.device.startup_commands
        )

        self._protocol.incremental = self.incremental or None
        self._protocol.prompt = self.prompt or None
        self._protocol.with_errors = self.with_errors or None
        self._protocol.timeout = self.timeout or None
        self._protocol.command_interval = self.command_interval or None

    def dataReceived(self, data):
        """Callback for when data is received.

        Once data is received in the channel we defer to the protocol level dataReceived method.
        """
        self._protocol.dataReceived(data)
        # SSHChannel.dataReceived(self, data)


class _TriggerUserAuth(_UserAuth):
    """Perform user authentication over SSH."""
    # The preferred order in which SSH authentication methods are tried.
    preferredOrder = settings.SSH_AUTHENTICATION_ORDER

    def getPassword(self, prompt=None):
        """Send along the password."""
        log.msg('Performing password authentication', debug=True)
        return defer.succeed(self.password)

    def getGenericAnswers(self, name, information, prompts):
        """
        Send along the password when authentication mechanism is not 'password'
        This is most commonly the case with 'keyboard-interactive', which even
        when configured within self.preferredOrder, does not work using default
        getPassword() method.
        """
        log.msg('Performing interactive authentication', debug=True)
        log.msg('Prompts: %r' % prompts, debug=True)

        # The response must always a sequence, and the length must match that
        # of the prompts list
        response = [''] * len(prompts)
        for idx, prompt_tuple in enumerate(prompts):
            prompt, echo = prompt_tuple  # e.g. [('Password: ', False)]
            if 'assword' in prompt:
                log.msg("Got password prompt: %r, sending password!" % prompt,
                        debug=True)
                response[idx] = self.password

        return defer.succeed(response)

    def ssh_USERAUTH_FAILURE(self, packet):
        """
        An almost exact duplicate of SSHUserAuthClient.ssh_USERAUTH_FAILURE
        modified to forcefully disconnect. If we receive authentication
        failures, instead of looping until the server boots us and performing a
        sendDisconnect(), we raise a `~trigger.exceptions.LoginFailure` and
        call loseConnection().
        See the base docstring for the method signature.
        """
        canContinue, partial = common.getNS(packet)
        partial = ord(partial)
        log.msg('Previous method: %r ' % self.lastAuth, debug=True)

        # If the last method succeeded, track it. If network devices ever start
        # doing second-factor authentication this might be useful.
        if partial:
            self.authenticatedWith.append(self.lastAuth)
        # If it failed, track that too...
        else:
            log.msg('Previous method failed, skipping it...', debug=True)
            self.authenticatedWith.append(self.lastAuth)

        def orderByPreference(meth):
            """
            Invoked once per authentication method in order to extract a
            comparison key which is then used for sorting.
            @param meth: the authentication method.
            @type meth: C{str}
            @return: the comparison key for C{meth}.
            @rtype: C{int}
            """
            if meth in self.preferredOrder:
                return self.preferredOrder.index(meth)
            else:
                # put the element at the end of the list.
                return len(self.preferredOrder)

        canContinue = sorted([meth for meth in canContinue.split(',')
                              if meth not in self.authenticatedWith],
                             key=orderByPreference)

        log.msg('Can continue with: %s' % canContinue)
        log.msg('Already tried: %s' % self.authenticatedWith, debug=True)
        return self._cbUserauthFailure(None, iter(canContinue))

    def _cbUserauthFailure(self, result, iterator):
        """Callback for ssh_USERAUTH_FAILURE"""
        if result:
            return
        try:
            method = iterator.next()
        except StopIteration:
            msg = (
                'No more authentication methods available.\n'
                'Tried: %s\n'
                'If not using ssh-agent w/ public key, make sure '
                'SSH_AUTH_SOCK is not set and try again.\n'
                % (self.preferredOrder,)
            )
            self.transport.factory.err = exceptions.LoginFailure(msg)
            self.transport.loseConnection()
        else:
            d = defer.maybeDeferred(self.tryAuth, method)
            d.addCallback(self._cbUserauthFailure, iterator)
            return d

class _TriggerCommandTransport(_CommandTransport):
    def connectionMade(self):
        """
        Once the connection is up, set the ciphers but don't do anything else!
        """
        self.currentEncryptions = transport.SSHCiphers(
            'none', 'none', 'none', 'none'
        )
        self.currentEncryptions.setKeys('', '', '', '', '', '')

    # FIXME(jathan): Make sure that this isn't causing a regression to:
    # https://github.com/trigger/trigger/pull/198
    def dataReceived(self, data):
        """
        Explicity override version detection for edge cases where "SSH-"
        isn't on the first line of incoming data.
        """
        # Store incoming data in a local buffer until we've detected the
        # presence of 'SSH-', then handover to default .dataReceived() for
        # version banner processing.
        if not hasattr(self, 'my_buf'):
            self.my_buf = ''
        self.my_buf = self.my_buf + data

        preVersion = self.gotVersion

        # One extra loop should be enough to get the banner to come through.
        if not self.gotVersion and b'SSH-' not in self.my_buf:
            return

        # This call should populate the SSH version and carry on as usual.
        _CommandTransport.dataReceived(self, data)

        # We have now seen the SSH version in the banner.
        # signal that the connection has been made successfully.
        if self.gotVersion and not preVersion:
            _CommandTransport.connectionMade(self)

    def connectionSecure(self):
        """
        When the connection is secure, start the authentication process.
        """
        self._state = b'AUTHENTICATING'

        command = _ConnectionReady(self.connectionReady)

        self._userauth = _TriggerUserAuth(self.creator.username, command)
        self._userauth.password = self.creator.password
        if self.creator.keys:
            self._userauth.keys = list(self.creator.keys)

        if self.creator.agentEndpoint is not None:
            d = self._userauth.connectToAgent(self.creator.agentEndpoint)
        else:
            d = defer.succeed(None)

        def maybeGotAgent(ignored):
            self.requestService(self._userauth)
        d.addBoth(maybeGotAgent)


class _TriggerSessionTransport(_TriggerCommandTransport):
    def verifyHostKey(self, hostKey, fingerprint):
        hostname = self.creator.hostname
        ip = self.transport.getPeer().host

        self._state = b'SECURING'
        return defer.succeed(1)


class _NewTriggerConnectionHelperBase(_NewConnectionHelper):
    """
    Return object used for establishing an async session rather than executing
    a single command.
    """
    def __init__(self, reactor, device, port, username, keys, password,
            agentEndpoint, knownHosts, ui):
        self.reactor = reactor
        self.device = device
        self.hostname = device.nodeName
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


class TriggerEndpointClientFactory(protocol.Factory):
    """
    Factory for all clients. Subclass me.
    """
    def __init__(self, creds=None, init_commands=None):
        self.creds = tacacsrc.validate_credentials(creds)
        self.results = []
        self.err = None

        # Setup and run the initial commands
        if init_commands is None:
            init_commands = []  # We need this to be a list
        self.init_commands = init_commands
        log.msg('INITIAL COMMANDS: %r' % self.init_commands, debug=True)
        self.initialized = False

    def clientConnectionFailed(self, connector, reason):
        """Do this when the connection fails."""
        log.msg('Client connection failed. Reason: %s' % reason)
        self.d.errback(reason)

    def clientConnectionLost(self, connector, reason):
        """Do this when the connection is lost."""
        log.msg('Client connection lost. Reason: %s' % reason)
        if self.err:
            log.msg('Got err: %r' % self.err)
            # log.err(self.err)
            self.d.errback(self.err)
        else:
            log.msg('Got results: %r' % self.results)
            self.d.callback(self.results)

    def stopFactory(self):
        # IF we're out of channels, shut it down!
        log.msg('All done!')

    def _init_commands(self, protocol):
        """
        Execute any initial commands specified.

        :param protocol: A Protocol instance (e.g. action) to which to write
        the commands.
        """
        if not self.initialized:
            log.msg('Not initialized, sending init commands', debug=True)
            for next_init in self.init_commands:
                log.msg('Sending: %r' % next_init, debug=True)
                protocol.write(next_init + '\r\n')
            else:
                self.initialized = True

    def connection_success(self, conn, transport):
        log.msg('Connection success.')
        self.conn = conn
        self.transport = transport
        log.msg('Connection information: %s' % self.transport)

class TriggerSSHShellClientEndpointBase(SSHCommandClientEndpoint):
    """
    Base class for SSH endpoints.

    Subclass me when you want to create a new ssh client.
    """
    @classmethod
    def newConnection(cls, reactor, username, device, keys=None, password=None,
                      port=22, agentEndpoint=None, knownHosts=None, ui=None):

        helper = _NewTriggerConnectionHelperBase(
            reactor, device, port, username, keys, password, agentEndpoint,
            knownHosts, ui
        )
        return cls(helper)

    @classmethod
    def existingConnection(cls, connection):
        """Overload stock existinConnection to not require ``commands``."""
        helper = _ExistingConnectionHelper(connection)
        return cls(helper)

    def __init__(self, creator):
        self._creator = creator

    def _executeCommand(self, connection, protocolFactory, command, incremental,
            with_errors, prompt_pattern, timeout, command_interval):
        """Establish the session on a given endpoint.

        For IOS like devices this is normally just a null string.
        """
        commandConnected = defer.Deferred()
        def disconnectOnFailure(passthrough):
            # Close the connection immediately in case of cancellation, since
            # that implies user wants it gone immediately (e.g. a timeout):
            immediate =  passthrough.check(CancelledError)
            self._creator.cleanupConnection(connection, immediate)
            return passthrough
        commandConnected.addErrback(disconnectOnFailure)

        channel = _TriggerShellChannel(
                self._creator, command, protocolFactory, commandConnected, incremental,
                with_errors, prompt_pattern, timeout, command_interval)
        connection.openChannel(channel)
        self.connected = True
        return commandConnected

    def connect(self, factory, command='', incremental=None,
            with_errors=None, prompt_pattern=None, timeout=0,
            command_interval=1):
        """Method to initiate SSH connection to device.

        :param factory: Trigger factory responsible for setting up connection
        :type factory: `~trigger.twister2.TriggerEndpointClientFactory`
        """
        d = self._creator.secureConnection()
        d.addCallback(self._executeCommand, factory, command, incremental,
                with_errors, prompt_pattern, timeout, command_interval)
        return d


class IoslikeSendExpect(protocol.Protocol, TimeoutMixin):
    """
    Action for use with TriggerTelnet as a state machine.

    Take a list of commands, and send them to the device until we run out or
    one errors. Wait for a prompt after each.
    """
    def __init__(self):
        self.device = None
        self.commands = []
        self.commanditer = iter(self.commands)
        self.connected = False
        self.disconnect = False
        self.initialized = False
        self.startup_commands = []
        # FIXME(tom) This sux and should be set by trigger settings
        self.timeout = 10
        self.on_error = defer.Deferred()
        self.todo = deque()
        self.done = None
        self.doneLock = defer.DeferredLock()

    def connectionMade(self):
        """Do this when we connect."""
        self.connected = True
        self.finished = defer.Deferred()
        self.results = self.factory.results = []
        self.data = ''
        log.msg('[%s] connectionMade, data: %r' % (self.device, self.data))
        # self.factory._init_commands(self)

    def connectionLost(self, reason):
        self.finished.callback(None)


        # Don't call _send_next, since we expect to see a prompt, which
        # will kick off initialization.

    def _schedule_commands(self, results, commands):
        """Schedule commands onto device loop.

        This is the actual routine to schedule a set of commands onto a device.

        :param results: Typical twisted results deferred
        :type  results: twisted.internet.defer
        :param commands: List containing commands to schedule onto device loop.
        :type commands: list
        """
        d = defer.Deferred()
        self.todo.append(d)
        
        # Schedule next command to run after the previous
        # has finished.
        if self.done and self.done.called is False:
            self.done.addCallback(
                    self._schedule_commands,
                    commands
                    )
            self.done = d
            return d

        # First iteration, setup the previous results deferred.
        if not results and self.done is None:
            self.done = defer.Deferred() 
            self.done.callback(None)

        # Either initial state or we are ready to execute more commands.
        if results or self.done is None or self.done.called:
            log.msg("SCHEDULING THE FOLLOWING {0} :: {1} WAS PREVIOUS RESULTS".format( commands, self.done))
            self.commands = commands
            self.commanditer = iter(commands)
            self._send_next()
            self.done = d

        # Each call must return a deferred.
        return d

    def add_commands(self, commands, on_error):
        """Add commands to abstract list of outstanding commands to execute

        The public method for `~trigger.netdevices.NetDevice` to use for appending more commands
        onto the device loop.

        :param commands: A list of commands to schedule onto device"
        :type  commands: list
        :param on_error: Error handler
        :type  on_error: func
        """
        # Exception handler to be used in case device throws invalid command warning.
        self.on_error.addCallback(on_error)
        d = self.doneLock.run(self._schedule_commands, None, commands)
        return d

    def dataReceived(self, bytes):
        """Do this when we get data."""
        log.msg('[%s] BYTES: %r' % (self.device, bytes))
        self.data += bytes # See if the prompt matches, and if it doesn't, see if it is waiting
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
            log.msg('[%s] No more commands to send, moving on...' %
                    self.device)

            if self.todo:
                payload = list(reversed(self.results))[:len(self.commands)]
                payload.reverse()
                d = self.todo.pop()
                d.callback(payload)
                return d
            else:
                return

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
