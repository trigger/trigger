# -*- coding: utf-8 -*-

"""
Login and basic command-line interaction support using the Twisted asynchronous
I/O framework. The Trigger Twister is just like the Mersenne Twister, except not at all.
"""

__author__ = 'Jathan McCollum, Eileen Tschetter, Mark Thomas, Michael Shields'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2006-2012, AOL Inc.'

from copy import copy
import fcntl
import os
import re
import signal
import socket
import struct
import sys
import time
import tty
from xml.etree.ElementTree import Element, ElementTree, XMLTreeBuilder, tostring
from twisted.conch.ssh.channel import SSHChannel
from twisted.conch.ssh.common import getNS, NS
from twisted.conch.ssh.connection import SSHConnection
from twisted.conch.ssh.session import packRequest_pty_req
from twisted.conch.ssh.transport import (DISCONNECT_CONNECTION_LOST,
                                         DISCONNECT_HOST_NOT_ALLOWED_TO_CONNECT,
                                         DISCONNECT_NO_MORE_AUTH_METHODS_AVAILABLE)
from twisted.conch.ssh.transport import SSHClientTransport
from twisted.conch.ssh.userauth import SSHUserAuthClient
from twisted.conch.telnet import Telnet, TelnetProtocol, ProtocolTransportMixin
from twisted.internet import defer, reactor, stdio
from twisted.internet.error import ConnectionDone, ConnectionLost
from twisted.internet.error import ConnectionRefusedError
from twisted.internet.protocol import ClientFactory, Protocol
from twisted.protocols.policies import TimeoutMixin
from twisted.python import log

from trigger.conf import settings
from trigger import tacacsrc, exceptions
from trigger.utils import network, cli

# Exports
# TODO (jathan): Setting this prevents everything from showing up in the Sphinx
# docs; so let's make sure we account for that ;)
#__all__ = ('connect', 'execute', 'stop_reactor')


# Constants
CONTINUE_PROMPTS = ['continue?', 'proceed?', '(y/n):', '[y/n]:']
DEFAULT_PROMPT_PAT = r'\S+#' # Will match most hardware
IOSLIKE_PROMPT_PAT = r'\S+(\(config(-[a-z:1-9]+)?\))?#'
SCREENOS_PROMPT_PAT = '(\w+?:|)[\w().-]*\(?([\w.-])?\)?\s*->\s*$'
NETSCALER_PROMPT_PAT = '\sDone\n$' # ' Done \n' only


# Functions
#==================
# Helper functions
#==================
def has_junoscript_error(tag):
    """Test whether an Element contains a Junoscript xnm:error."""
    if ElementTree(tag).find('.//{http://xml.juniper.net/xnm/1.1/xnm}error'):
        return True
    return False

def has_ioslike_error(s):
    """Test whether a string seems to contain an IOS-like error."""
    tests = (
        s.startswith('%'),     # Cisco, Arista
        '\n%' in s,            # Foundry
        'syntax error: ' in s, # Brocade VDX
    )

    return any(tests)

def has_netscaler_error(s):
    """Test whether a string seems to contain a NetScaler error."""
    return s.startswith('ERROR:')

def is_awaiting_confirmation(prompt):
    """
    Checks if a prompt is asking for us for confirmation and returns a Boolean.

    :param prompt: The prompt string to check
    """
    log.msg('Got confirmation prompt: %r' % prompt)
    prompt = prompt.lower()
    matchlist = CONTINUE_PROMPTS
    return any(prompt.endswith(match) for match in matchlist)

def stop_reactor():
    """Stop the reactor if it's already running."""
    from twisted.internet import reactor
    if reactor.running:
        reactor.stop()

#==================
# PTY functions
#==================
def pty_connect(device, action, creds=None, display_banner=None,
                ping_test=False, init_commands=None):
    """
    Connect to a ``device`` and log in. Use SSHv2 or telnet as appropriate.

    :param device:
        A `~trigger.netdevices.NetDevice` object.

    :param action:
        A Twisted ``Protocol`` instance (not class) that will be activated when
        the session is ready.

    :param creds:
        A 2-tuple (username, password). By default, credentials from
        ``.tacacsrc`` will be used according to ``settings.DEFAULT_REALM``.
        Override that here.

    :param display_banner:
        Will be called for SSH pre-authentication banners. It will receive two
        args, ``banner`` and ``language``. By default, nothing will be done
        with the banner.

    :param ping_test:
        If set, the device is pinged and must succeed in order to proceed.

    :param init_commands:
        A list of commands to execute upon logging into the device.

    :returns: A Twisted ``Deferred`` object
    """
    d = defer.Deferred()

    # Only proceed if ping succeeds
    if ping_test:
        log.msg('Pinging %s' % device, debug=True)
        if not network.ping(device.nodeName):
            log.msg('Ping to %s failed' % device, debug=True)
            return None

    # SSH?
    #log.msg('SSH TYPES: %s' % settings.SSH_TYPES, debug=True)
    if device.can_ssh_pty():
        log.msg('SSH connection test PASSED')
        if hasattr(sys, 'ps1') or not sys.stderr.isatty() \
         or not sys.stdin.isatty() or not sys.stdout.isatty():
            # Shell not in interactive mode.
            pass

        else:
            if not creds and device.is_firewall():
                creds = tacacsrc.get_device_password(device.nodeName)

        factory = TriggerSSHPtyClientFactory(d, action, creds, display_banner,
                                             init_commands)
        log.msg('Trying SSH to %s' % device, debug=True)
        port = 22
        #reactor.connectTCP(device.nodeName, 22, factory)

    # or Telnet?
    else:
        log.msg('SSH connection test FAILED, falling back to telnet')
        factory = TriggerTelnetClientFactory(d, action, creds,
                                             init_commands=init_commands)
        log.msg('Trying telnet to %s' % device, debug=True)
        port = 23
        #reactor.connectTCP(device.nodeName, 23, factory)

    reactor.connectTCP(device.nodeName, port, factory)
    print '\nFetching credentials from %s' % factory.tcrc.file_name

    return d

login_failed = None
def handle_login_failure(failure):
    """
    An errback to try detect a login failure

    :param failure:
        A Twisted ``Failure`` instance
    """
    global login_failed
    login_failed = failure

def connect(device, init_commands=None, output_logger=None, login_errback=None,
            reconnect_handler=None):
    """
    Connect to a network device via pty for an interactive shell.

    :param device:
        A `~trigger.netdevices.NetDevice` object.

    :param init_commands:
        (Optional) A list of commands to execute upon logging into the device.
        If not set, they will be attempted to be read from ``.gorc``.

    :param output_logger:
        (Optional) If set all data received by the device, including user
        input, will be written to this logger. This logger must behave like a
        file-like object and a implement a `.write()` method. Hint: Use
        ``StringIO``.

    :param login_errback:
        (Optional) An callable to be used as an errback that will handle the
        login failure behavior. If not set the default handler will be used.

    :param reconnect_handler:
        (Optional) A callable to handle the behavior of an authentication
        failure after a login has failed. If not set default handler will be
        used.
    """
    # Need to pass ^C through to the router so we can abort traceroute, etc.
    print 'Connecting to %s.  Use ^X to exit.' % device

    # Fetch the initial commands for the device
    if init_commands is None:
        from trigger import gorc
        init_commands = gorc.get_init_commands(device.vendor)

    # Sane defaults
    if login_errback is None:
        login_errback = handle_login_failure
    if reconnect_handler is None:
        reconnect_handler = cli.update_password_and_reconnect

    try:
        d = pty_connect(device, Interactor(log_to=output_logger),
                        init_commands=init_commands)
        d.addErrback(login_errback)
        d.addErrback(log.err)
        d.addCallback(lambda x: stop_reactor())
    except AttributeError, err:
        sys.stderr.write('Could not connect to %s.\n' % device)
        return 2 # Bad exit code

    cli.setup_tty_for_pty(reactor.run)

    # If there is a login failure stop the reactor so we can take raw_input(),
    # ask the user if they, want to update their cached credentials, and
    # prompt them to connect. Otherwise just display the error message and
    # exit.
    if login_failed is not None:
        stop_reactor()

        #print '\nLogin failed for the following reason:\n'
        print '\nConnection failed for the following reason:\n'
        print '%s\n' % login_failed.value

        if login_failed.type == exceptions.LoginFailure:
            reconnect_handler(device.nodeName)

        print 'BYE'

    return 0 # Good exit code

#==================
# Execute Factory functions
#==================
def _choose_execute(device):
    """
    Return the appropriate execute_ function for the given ``device`` based on
    platform and SSH/Telnet availability.

    :param device:
        A `~trigger.netdevices.NetDevice` object.
    """
    if device.is_ioslike():
        _execute = execute_ioslike
    elif device.is_netscaler():
        _execute = execute_netscaler
    elif device.is_netscreen():
        _execute = execute_netscreen
    elif device.vendor == 'juniper':
        _execute = execute_junoscript
    else:
        def null(*args, **kwargs):
            """Does nothing."""
            return None
        _execute = null

    return _execute

def execute(device, commands, creds=None, incremental=None, with_errors=False,
            timeout=settings.DEFAULT_TIMEOUT, command_interval=0):
    """
    Connect to a ``device`` and sequentially execute all the commands in the
    iterable ``commands``.

    Returns a Twisted ``Deferred`` object, whose callback will get a sequence
    of all the results after the connection is finished.

    ``commands`` is usually just a list, however, you can have also make it a
    generator, and have it and ``incremental`` share a closure to some state
    variables. This allows you to determine what commands to execute
    dynamically based on the results of previous commands. This implementation
    is experimental and it might be a better idea to have the ``incremental``
    callback determine what command to execute next; it could then be a method
    of an object that keeps state.

        BEWARE: Your generator cannot block; you must immediately
        decide what next command to execute, if any.

    Any ``None`` in the command sequence will result in a ``None`` being placed in
    the output sequence, with no command issued to the device.

    If any command returns an error, the connection is dropped immediately and
    the errback will fire with the failed command. You may set ``with_errors``
    to get the exception objects in the list instead.

    Connection failures will still fire the errback.

    `~trigger.exceptions.LoginTimeout` errors are always possible if the login
    process takes longer than expected and cannot be disabled.

    :param device:
        A `~trigger.netdevices.NetDevice` object

    :param commands:
        An iterable of commands to execute (without newlines).

    :param creds:
        (Optional) A 2-tuple of (username, password). If unset it will fetch it
        from ``.tacacsrc``.

    :param incremental:
        (Optional) A callback that will be called with an empty sequence upon
        connection and then called every time a result comes back from the
        device, with the list of all results.

    :param with_errors:
        (Optional) Return exceptions as results instead of raising them

    :param timeout:
        (Optional) Command response timeout in seconds. Set to ``None`` to
        disable. The default is in ``settings.DEFAULT_TIMEOUT``.
        `~trigger.exceptions.CommandTimeout` errors will result if a command seems
        to take longer to return than specified.

    :param command_interval:
        (Optional) Amount of time in seconds to wait between sending commands.

    :returns: A Twisted ``Deferred`` object
    """
    execute_func = _choose_execute(device)
    return execute_func(device=device, commands=commands, creds=creds,
                        incremental=incremental, with_errors=with_errors,
                        timeout=timeout, command_interval=command_interval)

def execute_generic_ssh(device, commands, creds=None, incremental=None,
                        with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                        command_interval=0, channel=None, prompt_pattern=None,
                        method='Generic'):
    """
    Use default SSH channel to execute commands on a device. Should work with
    anything not wonky.

    Please see `~trigger.twister.execute` for a full description of the
    arguments and how this works.
    """
    d = defer.Deferred()

    # Fallback to sane defaults if they aren't specified
    if channel is None:
        channel = TriggerSSHGenericChannel
    if prompt_pattern is None:
        prompt_pattern = DEFAULT_PROMPT_PAT

    factory = TriggerSSHChannelFactory(d, commands, creds, incremental,
                                       with_errors, timeout, channel,
                                       command_interval, prompt_pattern)

    log.msg('Trying %s SSH to %s' % (method, device), debug=True)
    reactor.connectTCP(device.nodeName, 22, factory)
    return d


def execute_junoscript(device, commands, creds=None, incremental=None,
                       with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                       command_interval=0):
    """
    Connect to a Juniper device and enable Junoscript XML mode. All commands
    are expected to be XML commands (ElementTree.Element objects suitable for
    wrapping in ``<rpc>`` elements). Errors are expected to be of type
    ``xnm:error``. Note that prompt detection is not used here.

    Please see `~trigger.twister.execute` for a full description of the
    arguments and how this works.
    """

    assert device.vendor == 'juniper'

    channel = TriggerSSHJunoscriptChannel
    prompt_pattern = ''
    method = 'Junoscript'
    return execute_generic_ssh(device, commands, creds, incremental,
                               with_errors, timeout, command_interval, channel,
                               prompt_pattern, method)

def execute_ioslike(device, commands, creds=None, incremental=None,
                    with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                    command_interval=0, loginpw=None, enablepw=None):
    """
    Execute commands on a Cisco/IOS-like device. It will automatically try to
    connect using SSH if it is available and not disabled in ``settings.py``.
    If SSH is unavailable, it will fallback to telnet unless that is also
    disabled in the settings. Otherwise it will fail, so you should probably
    make sure one or the other is enabled!

    Please see `~trigger.twister.execute` for a full description of the
    arguments and how this works.
    """
    # Try SSH if it's available and enabled
    if device.can_ssh_async():
        log.msg('execute_ioslike: SSH ENABLED for %s' % device.nodeName)
        #return execute_ioslike_ssh(device, commands, *args, **kwargs)
        return execute_ioslike_ssh(device=device, commands=commands,
                                   creds=creds, incremental=incremental,
                                   with_errors=with_errors, timeout=timeout,
                                   command_interval=command_interval)

    # Fallback to telnet if it's enabled
    elif settings.TELNET_ENABLED:
        log.msg('execute_ioslike: TELNET ENABLED for %s' % device.nodeName)
        #return execute_ioslike_telnet(device, commands, *args, **kwargs)
        return execute_ioslike_telnet(device=device, commands=commands,
                                      creds=creds, incremental=incremental,
                                      with_errors=with_errors, timeout=timeout,
                                      command_interval=command_interval,
                                      loginpw=loginpw, enablepw=enablepw)

    else:
        msg = 'Both SSH and telnet either failed or are disabled.'
        raise exceptions.ConnectionFailure(msg)

def execute_ioslike_telnet(device, commands, creds=None, incremental=None,
                           with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                           command_interval=0, loginpw=None, enablepw=None):
    """
    Execute commands via telnet on a Cisco/IOS-like device.

    Please see `~trigger.twister.execute` for a full description of the
    arguments and how this works.
    """
    assert device.is_ioslike()

    d = defer.Deferred()
    action = IoslikeSendExpect(device, commands, incremental, with_errors,
                               timeout, command_interval)
    factory = TriggerTelnetClientFactory(d, action, creds, loginpw, enablepw)

    log.msg('Trying IOS-like scripting to %s' % device, debug=True)
    reactor.connectTCP(device.nodeName, 23, factory)
    return d

def execute_ioslike_ssh(device, commands, creds=None, incremental=None,
                        with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                        command_interval=0):
    """
    Execute via SSH for IOS-like devices with some exceptions.

    Currently confirmed for A10, Brocade MLX, and Cisco only. For all other
    IOS-like vendors will use telnet for now. :(

    Please see `~trigger.twister.execute` for a full description of the
    arguments and how this works.
    """
    assert device.is_ioslike()

    channel = TriggerSSHGenericChannel
    prompt_pattern = IOSLIKE_PROMPT_PAT
    method = 'IOS-like'
    return execute_generic_ssh(device, commands, creds, incremental,
                               with_errors, timeout, command_interval, channel,
                               prompt_pattern, method)

def execute_netscreen(device, commands, creds=None, incremental=None,
                      with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                      command_interval=0):
    """
    Execute commands on a NetScreen device running ScreenOS. For NetScreen
    devices running Junos, use `~trigger.twister.execute_junoscript`.

    Please see `~trigger.twister.execute` for a full description of the
    arguments and how this works.
    """
    assert device.is_netscreen()

    # We live in a world where not every NetScreen device is local and can use
    # TACACS, so we must store unique credentials for each NetScreen device.
    if not creds:
        creds = tacacsrc.get_device_password(device.nodeName)

    channel = TriggerSSHGenericChannel
    prompt_pattern = SCREENOS_PROMPT_PAT
    method = 'NetScreen'
    return execute_generic_ssh(device, commands, creds, incremental,
                               with_errors, timeout, command_interval, channel,
                               prompt_pattern, method)

def execute_netscaler(device, commands, creds=None, incremental=None,
                      with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                      command_interval=0):
    """
    Execute commands on a NetScaler device.

    Please see `~trigger.twister.execute` for a full description of the
    arguments and how this works.
    """
    assert device.is_netscaler()

    channel = TriggerSSHNetscalerChannel
    prompt_pattern = NETSCALER_PROMPT_PAT
    method = 'NetScaler'
    return execute_generic_ssh(device, commands, creds, incremental,
                               with_errors, timeout, command_interval, channel,
                               prompt_pattern, method)


# Classes
#==================
# Client Basics
#==================
class TriggerClientFactory(ClientFactory):
    """
    Factory for all clients. Subclass me.
    """

    def __init__(self, deferred, creds=None, init_commands=None):
        self.d = deferred
        self.tcrc = tacacsrc.Tacacsrc()
        if creds is None:
            log.msg('creds not defined, fetching...', debug=True)
            realm = settings.DEFAULT_REALM
            creds = self.tcrc.creds.get(realm, tacacsrc.get_device_password(realm))
        self.creds = creds

        self.results = None
        self.err = None

        # Setup and run the initial commands
        if init_commands is None:
            init_commands = [] # We need this to be a list
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
            #log.err(self.err)
            self.d.errback(self.err)
        else:
            log.msg('Got results: %r' % self.results)
            self.d.callback(self.results)

    def _init_commands(self, protocol):
        """
        Execute any initial commands specified.

        :param protocol: A Protocol instance (e.g. action) to which to write
        the commands.
        """
        if not self.initialized:
            log.msg('Not initialized, sending init commands', debug=True)
            while self.init_commands:
                next_init = self.init_commands.pop(0)
                log.msg('Sending: %r' % next_init, debug=True)
                protocol.write(next_init + '\n')
            else:
                self.initialized = True

class TriggerSSHTransport(SSHClientTransport, object):
    """
    SSH transport with Trigger's defaults.

    Call with magic factory attributes 'creds', a tuple of login
    credentials, and 'channel', the class of channel to open.
    """

    def verifyHostKey(self, pubKey, fingerprint):
        """Verify host key, but don't actually verify. Awesome."""
        return defer.succeed(1)

    def connectionSecure(self):
        """Once we're secure, authenticate."""
        self.requestService(TriggerSSHUserAuth(
                self.factory.creds.username, TriggerSSHConnection()))

    def receiveError(self, reason, desc):
        """Do this when we receive an error."""
        self.sendDisconnect(reason, desc)

    def connectionLost(self, reason):
        """
        Detect when the transport connection is lost, such as when the
        remote end closes the connection prematurely (hosts.allow, etc.)

        :param reason: A Failure instance containing the error object
        """
        super(TriggerSSHTransport, self).connectionLost(reason)
        log.msg('Transport connection lost: %s' % reason.value)
        log.msg('%s' % dir(reason))

        # Only throw an error if this wasn't user-initiated (reason: 10)
        if getattr(self, 'disc_reason', None) == DISCONNECT_CONNECTION_LOST:
            pass
        elif reason.type == ConnectionLost:
            # Emulate the most common OpenSSH reason for this to happen
            msg = 'ssh_exchange_identification: Connection closed by remote host'
            #msg = 'Connection closed by remote host or in an unclean way'
            self.factory.err = exceptions.SSHConnectionLost(
                DISCONNECT_HOST_NOT_ALLOWED_TO_CONNECT, msg
            )

    def sendDisconnect(self, reason, desc):
        """Trigger disconnect of the transport."""
        log.msg('Got disconnect request, reason: %r, desc: %r' % (reason, desc), debug=True)
        if reason != DISCONNECT_CONNECTION_LOST:
            self.factory.err = exceptions.SSHConnectionLost(reason, desc)
        self.disc_reason = reason # This is checked in connectionLost()
        super(TriggerSSHTransport, self).sendDisconnect(reason, desc)

class TriggerSSHUserAuth(SSHUserAuthClient):
    """Perform user authentication over SSH."""
    # We are not yet in a world where network devices support publickey
    # authentication, so these are it.
    preferredOrder = ['password', 'keyboard-interactive']

    def getPassword(self, prompt=None):
        """Send along the password."""
        #self.getPassword()
        log.msg('Performing password authentication', debug=True)
        return defer.succeed(self.transport.factory.creds.password)

    def getGenericAnswers(self, name, information, prompts):
        """
        Send along the password when authentication mechanism is not 'password'.
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
            prompt, echo = prompt_tuple # e.g. [('Password: ', False)]
            if 'assword' in prompt:
                log.msg("Got password prompt: %r, sending password!" % prompt,
                        debug=True)
                response[idx] = self.transport.factory.creds.password

        return defer.succeed(response)

    def ssh_USERAUTH_BANNER(self, packet):
        """Display SSH banner."""
        if self.transport.factory.display_banner:
            banner, language = getNS(packet)
            self.transport.factory.display_banner(banner, language)

    def ssh_USERAUTH_FAILURE(self, packet):
        """
        An almost exact duplicate of SSHUserAuthClient.ssh_USERAUTH_FAILURE
        modified to forcefully disconnect. If we receive authentication
        failures, instead of looping until the server boots us and performing a
        sendDisconnect(), we raise a `~trigger.exceptions.LoginFailure` and
        call loseConnection().

        See the base docstring for the method signature.
        """
        canContinue, partial = getNS(packet)
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

        log.msg('can continue with: %s' % canContinue)
        log.msg('Already tried: %s' % self.authenticatedWith, debug=True)
        return self._cbUserauthFailure(None, iter(canContinue))

    def _cbUserauthFailure(self, result, iterator):
        """Callback for ssh_USERAUTH_FAILURE"""
        if result:
            return
        try:
            method = iterator.next()
        except StopIteration:
            #self.transport.sendDisconnect(
            #    DISCONNECT_NO_MORE_AUTH_METHODS_AVAILABLE,
            #    'no more authentication methods available')
            self.transport.factory.err = exceptions.LoginFailure(
                'No more authentication methods available')
            self.transport.loseConnection()
        else:
            d = defer.maybeDeferred(self.tryAuth, method)
            d.addCallback(self._cbUserauthFailure, iterator)
            return d

class TriggerSSHConnection(SSHConnection, object):
    """Used to manage, you know, an SSH connection."""

    def serviceStarted(self):
        """Open the channel once we start."""
        log.msg('channel = %r' % self.transport.factory.channel)
        self.openChannel(self.transport.factory.channel(conn=self))

    def channelClosed(self, channel):
        """Close the channel when we're done."""
        self.transport.loseConnection()

#==================
# SSH PTY Stuff
#==================
class Interactor(Protocol):
    """
    Creates an interactive shell.

    Intended for use as an action with pty_connect(). See gong for an example.
    """
    def __init__(self, log_to=None):
        self._log_to = log_to
        #Protocol.__init__(self)

    def _log(self, data):
        if self._log_to is not None:
            self._log_to.write(data)

    def connectionMade(self):
        """Fire up stdin/stdout once we connect."""
        c = Protocol()
        c.dataReceived = self.write
        self.stdio = stdio.StandardIO(c)

    def dataReceived(self, data):
        """And write data to the terminal."""
        log.msg('Interactor.dataReceived: %r' % data, debug=True)
        self._log(data)
        self.stdio.write(data)

class TriggerSSHPtyChannel(SSHChannel):
    """Used by pty_connect() to turn up an SSH pty channel."""
    name = 'session'

    def channelOpen(self, data):
        """Setup the terminal when the channel opens."""
        pr = packRequest_pty_req(os.environ['TERM'],
                                 self._get_window_size(), '')
        self.conn.sendRequest(self, 'pty-req', pr)
        self.conn.sendRequest(self, 'shell', '')
        signal.signal(signal.SIGWINCH, self._window_resized)

        # Setup and run the initial commands
        self.factory = self.conn.transport.factory
        self.factory._init_commands(protocol=self) # We are the protocol

        # Pass control to the action.
        action = self.conn.transport.factory.action
        action.write = self.write
        self.dataReceived = action.dataReceived
        self.extReceived = action.dataReceived
        self.connectionLost = action.connectionLost
        action.connectionMade()
        action.dataReceived(data)

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

class TriggerSSHPtyClientFactory(TriggerClientFactory):
    """
    Factory for an interactive SSH connection.

    'action' is a Protocol that will be connected to the session after login.
    Use it to interact with the user and pass along commands.
    """

    def __init__(self, deferred, action, creds=None, display_banner=None,
                 init_commands=None):
        self.protocol = TriggerSSHTransport
        self.action = action
        self.action.factory = self
        self.display_banner = display_banner
        self.channel = TriggerSSHPtyChannel
        TriggerClientFactory.__init__(self, deferred, creds, init_commands)

#==================
# SSH Channels
#==================
class TriggerSSHChannelFactory(TriggerClientFactory):
    """
    Intended to be used as a parent of automated SSH channels (e.g. Junoscript,
    NetScreen, NetScaler) to eliminate boiler plate in those subclasses.
    """

    def __init__(self, deferred, commands, creds=None, incremental=None,
                 with_errors=False, timeout=None, channel=None,
                 command_interval=0, prompt_pattern=None):

        if channel is None:
            raise TwisterError('You must specify an SSH channel class')

        if prompt_pattern is None:
            prompt_pattern = DEFAULT_PROMPT_PAT

        self.protocol = TriggerSSHTransport
        self.display_banner = None
        self.commands = commands
        self.incremental = incremental
        self.with_errors = with_errors
        self.timeout = timeout
        self.channel = channel
        self.command_interval = command_interval
        self.prompt = re.compile(prompt_pattern)
        TriggerClientFactory.__init__(self, deferred, creds)

class TriggerSSHChannelBase(SSHChannel, TimeoutMixin):
    """
    Base class for SSH channels.

    The method self._setup_channelOpen() should be called by channelOpen() in
    the subclasses. Before you subclass, however, see if you can't just use
    TriggerSSHGenericChannel as-is!
    """
    name = 'session'

    def _setup_channelOpen(self, data):
        """
        Call me in your subclass in self.channelOpen()::

            def channelOpen(self, data):
                self._setup_channelOpen(data)
                self.conn.sendRequest(self, 'shell', '')
                # etc.
        """
        self.factory = self.conn.transport.factory
        log.msg('COMMANDS: %r' % self.factory.commands)
        self.commanditer = iter(self.factory.commands)
        self.results = self.factory.results = []
        self.with_errors = self.factory.with_errors
        self.incremental = self.factory.incremental
        self.command_interval = self.factory.command_interval
        self.prompt = self.factory.prompt
        self.setTimeout(self.factory.timeout)
        self.initialize = [] # Commands to run at startup e.g. ['enable\n']

    def channelOpen(self, data):
        """Do this when the channel opens."""
        self._setup_channelOpen(data)
        self.initialized = False
        self.data = ''
        #self.conn.sendRequest(self, 'shell', '')
        self.conn.sendRequest(self, 'shell', '', wantReply=True).addCallback(self._gotResponse)

        # Don't call _send_next() here, since we expect to see a prompt, which
        # will kick off initialization.

    def _gotResponse(self, _):
        """
        Potentially useful if you want to do something after the shell is
        initialized.

        If the shell never establishes, this won't be called.
        """
        log.msg('Got response!')
        #self.write('\n')

    def dataReceived(self, bytes):
        """Do this when we receive data."""
        # Append to the data buffer
        self.data += bytes
        #log.msg('BYTES: %r' % bytes)
        #log.msg('BYTES: (left: %r, max: %r, bytes: %r, data: %r)' %
        #        (self.remoteWindowLeft, self.localMaxPacket, len(bytes), len(self.data)))

        # Keep going til you get a prompt match
        m = self.prompt.search(self.data)
        if not m:
            #log.msg('STATE: prompt match failure', debug=True)
            return None
        log.msg('STATE: prompt %r' % m.group(), debug=True)

        # Strip the prompt from the match result
        result = self.data[:m.start()]
        result = result[result.find('\n')+1:]

        # Only keep the results once we've sent any initial_commands
        if self.initialized:
            self.results.append(result)

        # By default we're checking for IOS-like errors because most vendors
        # fall under this category.
        if has_ioslike_error(result) and not self.with_errors:
            log.msg('ERROR: %r' % result, debug=True)
            self.factory.err = exceptions.CommandFailure(result)
            self.loseConnection()
            return None

        # Honor the command_interval and then send the next command in the
        # stack
        else:
            if self.command_interval > 0:
                time.sleep(self.command_interval)
            self._send_next()

    def _send_next(self):
        """Send the next command in the stack."""
        # Reset the timeout and the buffer for each new command
        self.resetTimeout()
        self.data = ''

        if not self.initialized:
            log.msg('COMMANDS NOT INITIALIZED')
            if self.initialize:
                self.write(self.initialize.pop(0))
                return None
            else:
                log.msg('Successfully initialized for command execution')
                self.initialized = True

        if self.incremental:
            self.incremental(self.results)

        try:
            next_command = self.commanditer.next()
        except StopIteration:
            log.msg('CHANNEL: out of commands, closing...', debug=True)
            self.loseConnection()
            return None

        if next_command is None:
            self.results.append(None)
            self._send_next()
        else:
            log.msg('sending SSH command %r' % next_command, debug=True)
            self.write(next_command + '\n')

    def loseConnection(self):
        """
        Terminate the connection. Link this to the transport method of the same
        name.
        """
        self.conn.transport.loseConnection()

    def timeoutConnection(self):
        """
        Do this when the connection times out.
        """
        self.factory.err = exceptions.CommandTimeout('Timed out while sending commands')
        self.loseConnection()

class TriggerSSHGenericChannel(TriggerSSHChannelBase):
    """
    An SSH channel using all of the Trigger defaults to interact with network
    devices that implement SSH without any tricks.

    Currently A10, Cisco, Brocade, NetScreen can simply use this. Nice!

    Before you create your own subclass, see if you can't use me as-is!
    """
    pass

class TriggerSSHJunoscriptChannel(TriggerSSHChannelBase):
    """
    An SSH channel to execute Junoscript commands on a Juniper device running
    Junos.

    This completely assumes that we are the only channel in the factory (a
    TriggerJunoscriptFactory) and walks all the way back up to the factory for
    its arguments.
    """

    def channelOpen(self, data):
        """Do this when channel opens."""
        self._setup_channelOpen(data)
        self.conn.sendRequest(self, 'exec', NS('junoscript'))
        _xml = '<?xml version="1.0" encoding="us-ascii"?>\n'
        _xml += '<junoscript version="1.0" hostname="%s" release="7.6R2.9">\n' % socket.getfqdn()
        self.write(_xml)
        self.xmltb = IncrementalXMLTreeBuilder(self._endhandler)

        self._send_next()

    def dataReceived(self, data):
        """Do this when we receive data."""
        #log.msg('BYTES: %r' % data, debug=True)
        self.xmltb.feed(data)

    def _send_next(self):
        """Send the next command in the stack."""
        self.resetTimeout()

        if self.incremental:
            self.incremental(self.results)

        try:
            next_command = self.commanditer.next()
            log.msg('COMMAND: next command=%s' % next_command, debug=True)

        except StopIteration:
            log.msg('CHANNEL: out of commands, closing...', debug=True)
            self.loseConnection()
            return None

        if next_command is None:
            self.results.append(None)
            self._send_next()
        else:
            rpc = Element('rpc')
            rpc.append(next_command)
            ElementTree(rpc).write(self)

    def _endhandler(self, tag):
        """Do this when the XML stream ends."""
        if tag.tag != '{http://xml.juniper.net/xnm/1.1/xnm}rpc-reply':
            return None # hopefully it's interior to an <rpc-reply>
        self.results.append(tag)

        if has_junoscript_error(tag) and not self.with_errors:
            self.factory.err = exceptions.JunoscriptCommandFailure(tag)
            self.loseConnection()
            return None

        # Honor the command_interval and then send the next command in the
        # stack
        else:
            if self.command_interval > 0:
                time.sleep(self.command_interval)
            self._send_next()

class TriggerSSHNetscalerChannel(TriggerSSHChannelBase):
    """
    An SSH channel to interact with Citrix NetScaler hardware.

    It's almost a generic SSH channel except that we must check for errors
    first, because a prompt is not returned when an error is received. This had
    to be accounted for in the ``dataReceived()`` method.
    """

    def dataReceived(self, bytes):
        """Do this when we receive data."""
        self.data += bytes
        #log.msg('BYTES: %r' % bytes, debug=True)
        #log.msg('BYTES: (left: %r, max: %r, bytes: %r, data: %r)' %
        #        (self.remoteWindowLeft, self.localMaxPacket, len(bytes), len(self.data)))

        # We have to check for errors first, because a prompt is not returned
        # when an error is received like on other systems.
        if has_netscaler_error(self.data):
            err = self.data
            if not self.with_errors:
                self.factory.err = exceptions.NetscalerCommandFailure(err)
                self.loseConnection()
                return None
            else:
                self.results.append(err)
                self._send_next()

        m = self.prompt.search(self.data)
        if not m:
            #log.msg('STATE: prompt match failure', debug=True)
            return None
        log.msg('STATE: prompt %r' % m.group(), debug=True)

        result = self.data[:m.start()] # Strip ' Done\n' from results.

        if self.initialized:
            self.results.append(result)

        if self.command_interval > 0:
            time.sleep(self.command_interval)

        self._send_next()

#==================
# XML Stuff (for Junoscript)
#==================
class IncrementalXMLTreeBuilder(XMLTreeBuilder):
    """
    Version of XMLTreeBuilder that runs a callback on each tag.

    We need this because JunoScript treats the entire session as one XML
    document. IETF NETCONF fixes that.
    """

    def __init__(self, callback, *args, **kwargs):
        self._endhandler = callback
        XMLTreeBuilder.__init__(self, *args, **kwargs)

    def _end(self, tag):
        """Do this when we're out of XML!"""
        return self._endhandler(XMLTreeBuilder._end(self, tag))


#==================
# Telnet Channels
#==================
class TriggerTelnetClientFactory(TriggerClientFactory):
    """
    Factory for a telnet connection.
    """

    def __init__(self, deferred, action, creds=None, loginpw=None,
                 enablepw=None, init_commands=None):
        self.protocol = TriggerTelnet
        self.action = action
        self.loginpw = loginpw
        self.enablepw = enablepw
        self.action.factory = self
        TriggerClientFactory.__init__(self, deferred, creds, init_commands)

class TriggerTelnet(Telnet, ProtocolTransportMixin, TimeoutMixin):
    """
    Telnet-based session login state machine. Primarily used by IOS-like type devices.
    """

    def __init__(self, timeout=settings.TELNET_TIMEOUT):
        self.protocol = TelnetProtocol()
        self.waiting_for = [
            ('Username: ', self.state_username),                  # Most
            ('Please Enter Login Name  : ', self.state_username), # OLD Foundry
            ('User Name:', self.state_username),                  # Dell
            ('login: ', self.state_username),                     # Arista, Juniper
            ('Password: ', self.state_login_pw),
        ]
        self.data = ''
        self.applicationDataReceived = self.login_state_machine
        self.timeout = timeout
        self.setTimeout(self.timeout)
        Telnet.__init__(self)

    def enableRemote(self, option):
        """
        Allow telnet clients to enable options if for some reason they aren't
        enabled already (e.g. ECHO). (Ref: http://bit.ly/wkFZFg) For some reason
        Arista Networks hardware is the only vendor that needs this method
        right now.
        """
        log.msg('TriggerTelnet.enableRemote option: %r' % option, debug=True)
        return True

    def login_state_machine(self, bytes):
        """Track user login state."""
        self.data += bytes
        log.msg('STATE:  got data %r' % self.data, debug=True)
        for (text, next_state) in self.waiting_for:
            log.msg('STATE:  possible matches %r' % text, debug=True)
            if self.data.endswith(text):
                log.msg('Entering state %r' % next_state.__name__, debug=True)
                self.resetTimeout()
                next_state()
                self.data = ''
                break

    def state_username(self):
        """After we've gotten username, check for password prompt."""
        self.write(self.factory.creds.username + '\n')
        self.waiting_for = [
            ('Password: ', self.state_password),
            ('Password:', self.state_password),  # Dell
        ]

    def state_password(self):
        """After we got password prompt, check for enabled prompt."""
        self.write(self.factory.creds.password + '\n')
        self.waiting_for = [
            ('#', self.state_logged_in),
            ('>', self.state_enable),
            ('> ', self.state_logged_in),             # Juniper
            ('\n% ', self.state_percent_error),
            ('# ', self.state_logged_in),             # Dell
            ('\nUsername: ', self.state_raise_error), # Cisco
            ('\nlogin: ', self.state_raise_error),    # Arista, Juniper
        ]

    def state_logged_in(self):
        """
        Once we're logged in, exit state machine and pass control to the
        action.
        """
        self.setTimeout(None)
        data = self.data.lstrip('\n')
        log.msg('state_logged_in, DATA: %r' % data, debug=True)
        del self.waiting_for, self.data

        # Run init_commands
        self.factory._init_commands(protocol=self) # We are the protocol

        # Control passed here :)
        action = self.factory.action
        action.transport = self
        self.applicationDataReceived = action.dataReceived
        self.connectionLost = action.connectionLost
        action.write = self.write
        action.loseConnection = self.loseConnection
        action.connectionMade()
        action.dataReceived(data)

    def state_enable(self):
        """
        Special Foundry breakage because they don't do auto-enable from
        TACACS by default. Use 'aaa authentication login privilege-mode'.
        Also, why no space after the Password: prompt here?
        """
        log.msg("ENABLE: Sending command: enable\n", debug=True)
        self.write('enable\n')
        self.waiting_for = [
            ('Password: ', self.state_enable_pw), # Foundry
            ('Password:', self.state_enable_pw),  # Dell
        ]

    def state_login_pw(self):
        """Pass the login password from the factory or NetDevices"""
        if self.factory.loginpw:
            pw = self.factory.loginpw
        else:
            from trigger.netdevices import NetDevices
            pw = NetDevices().find(self.transport.connector.host).loginPW

        # Workaround to avoid TypeError when concatenating 'NoneType' and
        # 'str'. This *should* result in a LoginFailure.
        if pw is None:
            pw = ''

        log.msg('Sending password %s' % pw, debug=True)
        self.write(pw + '\n')
        self.waiting_for = [('>', self.state_enable),
                            ('#', self.state_logged_in),
                            ('\n% ', self.state_percent_error),
                            ('incorrect password.', self.state_raise_error)]

    def state_enable_pw(self):
        """Pass the enable password from the factory or NetDevices"""
        if self.factory.enablepw:
            pw = self.factory.enablepw
        else:
            from trigger.netdevices import NetDevices
            pw = NetDevices().find(self.transport.connector.host).enablePW
        log.msg('Sending password %s' % pw, debug=True)
        self.write(pw + '\n')
        self.waiting_for = [('#', self.state_logged_in),
                            ('\n% ', self.state_percent_error),
                            ('incorrect password.', self.state_raise_error)]

    def state_percent_error(self):
        """
        Found a % error message. Don't return immediately because we
        don't have the error text yet.
        """
        self.waiting_for = [('\n', self.state_raise_error)]

    def state_raise_error(self):
        """Do this when we get a login failure."""
        self.waiting_for = []
        self.factory.err = exceptions.LoginFailure('%r' % self.data.rstrip())
        self.loseConnection()

    def timeoutConnection(self):
        """Do this when we timeout logging in."""
        self.factory.err = exceptions.LoginTimeout('Timed out while logging in')
        self.loseConnection()

class IoslikeSendExpect(Protocol, TimeoutMixin):
    """
    Action for use with TriggerTelnet as a state machine.

    Take a list of commands, and send them to the device until we run out or
    one errors. Wait for a prompt after each.
    """

    def __init__(self, dev, commands, incremental=None, with_errors=False,
                 timeout=None, command_interval=0):
        self.dev = dev
        self._commands = commands
        self.commanditer = iter(commands)
        self.incremental = incremental
        self.with_errors = with_errors
        self.timeout = timeout
        self.command_interval = command_interval
        self.prompt =  re.compile(IOSLIKE_PROMPT_PAT)

        # Commands used to disable paging.
        paging_map = {
            'cisco': 'terminal length 0\n',
            'arista': 'terminal length 0\n',
            'foundry': 'skip-page-display\n',
            'brocade': self._disable_paging_brocade(dev),
            'dell': 'terminal datadump\n',
        }
        self.initialize = [paging_map.get(dev.vendor.name)] # must be a list
        log.msg('My initialize commands: %r' % self.initialize, debug=True)
        self.initialized = False

    def _disable_paging_brocade(self, dev):
        """
        Brocade MLX routers and VDX switches require different commands to
        disable paging. Based on the device type, emits the proper command.

        :param dev: A Brocade NetDevice object
        """
        if dev.is_switch():
            return 'terminal length 0\n'
        elif dev.is_router():
            return 'skip-page-display\n'

        return None

    def connectionMade(self):
        """Do this when we connect."""
        self.setTimeout(self.timeout)
        self.results = self.factory.results = []
        self.data = ''
        log.msg('connectionMade, data: %r' % self.data, debug=True)
        # Don't call _send_next, since we expect to see a prompt, which
        # will kick off initialization.

    def dataReceived(self, bytes):
        """Do this when we get data."""
        log.msg('dataReceived, got bytes: %r' % bytes, debug=True)
        self.data += bytes
        log.msg('dataReceived, got data: %r' % self.data, debug=True)

        # See if the prompt matches, and if it doesn't, see if it is waiting
        # for more input (like a [y/n]) prompt), and continue, otherwise return
        # None
        m = self.prompt.search(self.data)
        if not m:
            # If the prompt confirms set the index to the matched bytes,
            if is_awaiting_confirmation(self.data):
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
        log.msg('IoslikeSendExpect.dataReceived result BEFORE: %r' % result, debug=True)
        result = result[result.find('\n')+1:]
        log.msg('IoslikeSendExpect.dataReceived result AFTER: %r' % result, debug=True)

        if self.initialized:
            self.results.append(result)

        if has_ioslike_error(result) and not self.with_errors:
            log.msg('ERROR: %r' % result, debug=True)
            self.factory.err = exceptions.IoslikeCommandFailure(result)
            self.loseConnection()
        else:
            if self.command_interval > 0:
                time.sleep(self.command_interval)
            self._send_next()

    def _send_next(self):
        """Send the next command in the stack."""
        self.data = ''
        self.resetTimeout()

        if not self.initialized:
            log.msg('Not initialized, sending init commands', debug=True)
            if self.initialize:
                next_init = self.initialize.pop(0)
                log.msg('Sending: %r' % next_init, debug=True)
                self.write(next_init)
                return None
            else:
                self.initialized = True

        if self.incremental:
            self.incremental(self.results)

        try:
            next_command = self.commanditer.next()
        except StopIteration:
            log.msg('No more commands to send, disconnecting...', debug=True)
            self.loseConnection()
            return None

        if next_command is None:
            self.results.append(None)
            self._send_next()
        else:
            log.msg('Sending command: %r' % next_command, debug=True)
            self.write(next_command + '\n')

    def timeoutConnection(self):
        """Do this when we timeout."""
        self.factory.err = exceptions.CommandTimeout('Timed out while sending commands')
        self.loseConnection()
