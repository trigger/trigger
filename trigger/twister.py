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


__author__ = 'Jathan McCollum, Eileen Tschetter, Mark Thomas, Michael Shields'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan@gmail.com'
__copyright__ = 'Copyright 2006-2013, AOL Inc.; 2013 Salesforce.com'
__version__ = '1.5.8'


# Exports
# TODO (jathan): Setting this prevents everything from showing up in the Sphinx
# docs; so let's make sure we account for that ;)
# __all__ = ('connect', 'execute', 'stop_reactor')


#  Functions
# ==================
#  Helper functions
# ==================
def has_junoscript_error(tag):
    """Test whether an Element contains a Junoscript xnm:error."""
    if ElementTree(tag).find('.//{http://xml.juniper.net/xnm/1.1/xnm}error'):
        return True
    return False


def has_juniper_error(s):
    """Test whether a string seems to contain an Juniper error."""
    tests = (
        'unknown command.' in s,
        'syntax error, ' in s,
        'invalid value.' in s,
        'missing argument.' in s,
    )
    return any(tests)


def has_ioslike_error(s):
    """Test whether a string seems to contain an IOS-like error."""
    tests = (
        s.startswith('%'),                  # Cisco, Arista
        '\n%' in s,                         # A10, Aruba, Foundry
        'syntax error: ' in s.lower(),      # Brocade VDX, F5 BIGIP
        s.startswith('Invalid input -> '),  # Brocade MLX
        s.endswith('Syntax Error'),         # MRV
    )
    return any(tests)


def has_netscaler_error(s):
    """Test whether a string seems to contain a NetScaler error."""
    tests = (
        s.startswith('ERROR: '),
        '\nERROR: ' in s,
        s.startswith('Warning: '),
        '\nWarning: ' in s,
    )
    return any(tests)


def is_awaiting_confirmation(prompt):
    """
    Checks if a prompt is asking for us for confirmation and returns a Boolean.

    New patterns may be added by customizing ``settings.CONTINUE_PROMPTS``.

    >>> from trigger.twister import is_awaiting_confirmation
    >>> is_awaiting_confirmation('Destination filename [running-config]? ')
    True

    :param prompt:
        The prompt string to check
    """
    prompt = prompt.lower()
    matchlist = settings.CONTINUE_PROMPTS
    return any(prompt.endswith(match.lower()) for match in matchlist)


def requires_enable(proto_obj, data):
    """
    Check if a device requires enable.

    :param proto_obj:
        A Protocol object such as an SSHChannel

    :param data:
        The channel data to check for an enable prompt
    """
    if not proto_obj.device.is_ioslike():
        log.msg('[%s] Not IOS-like, setting enabled flag' % proto_obj.device)
        proto_obj.enabled = True
        return None
    match = proto_obj.enable_prompt.search(data)
    if match is not None:
        log.msg('[%s] Enable prompt detected: %r' % (proto_obj.device,
                                                     match.group()))
    return match


def send_enable(proto_obj, disconnect_on_fail=True):
    """
    Send 'enable' and enable password to device.

    :param proto_obj:
        A Protocol object such as an SSHChannel

    :param disconnect_on_fail:
        If set, will forcefully disconnect on enable password failure
    """
    log.msg('[%s] Enable required, sending enable commands' % proto_obj.device)

    # Get enable password from env. or device object
    device_pw = getattr(proto_obj.device, 'enablePW', None)
    enable_pw = os.getenv('TRIGGER_ENABLEPW') or device_pw
    if enable_pw is not None:
        log.msg('[%s] Enable password detected, sending...' % proto_obj.device)
        proto_obj.data = ''  # Zero out the buffer before sending the password
        proto_obj.write('enable' + proto_obj.device.delimiter)

        # In low latency environments (< 1ms), we might send the password
        # before the "Password:" prommpt is displayed. Here we wait a split
        # second for the password prompt to appear before sending the
        # password. See: https://github.com/trigger/trigger/issues/238
        from twisted.internet import reactor
        reactor.callLater(
            0.1, proto_obj.write, enable_pw + proto_obj.device.delimiter
        )
        proto_obj.enabled = True
    else:
        log.msg('[%s] Enable password not found, not enabling.' %
                proto_obj.device)
        proto_obj.factory.err = exceptions.EnablePasswordFailure(
            'Enable password not set. See documentation on '
            'settings.TRIGGER_ENABLEPW for help.'
        )
        if disconnect_on_fail:
            proto_obj.loseConnection()


def stop_reactor():
    """Stop the reactor if it's already running."""
    from twisted.internet import reactor
    if reactor.running:
        log.msg('Stopping reactor')
        reactor.stop()

# ==================
#  PTY functions
# ==================


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
    if device.can_ssh_pty():
        interactive = hasattr(sys, 'ps1')
        all_tty = all(x.isatty() for x in (sys.stderr, sys.stdin, sys.stdout))
        log.msg('[%s] SSH connection test PASSED' % device)
        if interactive or not all_tty:
            # Shell not in interactive mode.
            pass

        else:
            if not creds and device.is_firewall():
                creds = tacacsrc.get_device_password(device.nodeName)

        factory = TriggerSSHPtyClientFactory(d, action, creds, display_banner,
                                             init_commands, device=device)
        port = device.nodePort or settings.SSH_PORT
        log.msg('Trying SSH to %s:%s' % (device, port), debug=True)

    # or Telnet?
    elif settings.TELNET_ENABLED:
        log.msg('[%s] SSH connection test FAILED, falling back to telnet' %
                device)
        factory = TriggerTelnetClientFactory(d,
                                             action,
                                             creds,
                                             init_commands=init_commands,
                                             device=device)
        port = device.nodePort or settings.TELNET_PORT
        log.msg('Trying telnet to %s:%s' % (device, port), debug=True)
    else:
        log.msg('[%s] SSH connection test FAILED, '
                'telnet fallback disabled' % device)
        return None

    reactor.connectTCP(device.nodeName, port, factory)
    # TODO (jathan): There has to be another way than calling Tacacsrc
    # construtor AGAIN...
    print '\nFetching credentials from %s' % tacacsrc.Tacacsrc().file_name

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
        init_commands = gorc.get_init_commands(device.vendor.name)

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
    except AttributeError as err:
        log.msg(err)
        sys.stderr.write('Could not connect to %s.\n' % device)
        return 2  # Bad exit code

    cli.setup_tty_for_pty(reactor.run)

    # If there is a login failure stop the reactor so we can take raw_input(),
    # ask the user if they, want to update their cached credentials, and
    # prompt them to connect. Otherwise just display the error message and
    # exit.
    if login_failed is not None:
        stop_reactor()

        # print '\nLogin failed for the following reason:\n'
        print '\nConnection failed for the following reason:\n'
        print '%s\n' % login_failed.value

        if login_failed.type == exceptions.LoginFailure:
            reconnect_handler(device.nodeName)

        print 'BYE'

    return 0  # Good exit code

# ==================
#  Execute Factory functions
# ==================


def _choose_execute(device, force_cli=False):
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
        if force_cli:
            _execute = execute_async_pty_ssh
        else:
            _execute = execute_junoscript
    elif device.is_pica8():
        _execute = execute_pica8
    else:
        _execute = execute_async_pty_ssh

    return _execute


def execute(
        device,
        commands,
        creds=None,
        incremental=None,
        with_errors=False,
        timeout=settings.DEFAULT_TIMEOUT,
        command_interval=0,
        force_cli=False
        ):
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

    Any ``None`` in the command sequence will result in a ``None`` being placed
    in the output sequence, with no command issued to the device.

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
        `~trigger.exceptions.CommandTimeout` errors will result if a command
        seems to take longer to return than specified.

    :param command_interval:
        (Optional) Amount of time in seconds to wait between sending commands.

    :param force_cli:
        (Optional) Juniper-only: Force use of CLI instead of Junoscript.

    :returns: A Twisted ``Deferred`` object
    """
    execute_func = _choose_execute(device, force_cli=force_cli)
    return execute_func(device=device, commands=commands, creds=creds,
                        incremental=incremental, with_errors=with_errors,
                        timeout=timeout, command_interval=command_interval)


def execute_generic_ssh(device, commands, creds=None, incremental=None,
                        with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                        command_interval=0, channel_class=None,
                        prompt_pattern=None, method='Generic',
                        connection_class=None):
    """
    Use default SSH channel to execute commands on a device. Should work with
    anything not wonky.

    Please see `~trigger.twister.execute` for a full description of the
    arguments and how this works.
    """
    d = defer.Deferred()

    # Fallback to sane defaults if they aren't specified
    if channel_class is None:
        channel_class = TriggerSSHGenericChannel
    if prompt_pattern is None:
        prompt_pattern = device.vendor.prompt_pattern
    if connection_class is None:
        connection_class = TriggerSSHConnection

    factory = TriggerSSHChannelFactory(d, commands, creds, incremental,
                                       with_errors, timeout, channel_class,
                                       command_interval, prompt_pattern,
                                       device, connection_class)

    port = device.nodePort or settings.SSH_PORT
    log.msg('Trying %s SSH to %s:%s' % (method, device, port), debug=True)
    reactor.connectTCP(device.nodeName, port, factory)
    return d


def execute_exec_ssh(device, commands, creds=None, incremental=None,
                     with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                     command_interval=0):
    """
    Use multiplexed SSH 'exec' command channels to execute commands.

    This will maintain a single SSH connection and run each new command in a
    separate channel after the previous command completes.

    Please see `~trigger.twister.execute` for a full description of the
    arguments and how this works.
    """
    channel_class = TriggerSSHCommandChannel
    prompt_pattern = ''
    method = 'Exec'
    connection_class = TriggerSSHMultiplexConnection
    return execute_generic_ssh(device, commands, creds, incremental,
                               with_errors, timeout, command_interval,
                               channel_class, prompt_pattern, method,
                               connection_class)


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

    channel_class = TriggerSSHJunoscriptChannel
    prompt_pattern = ''
    method = 'Junoscript'
    return execute_generic_ssh(device, commands, creds, incremental,
                               with_errors, timeout, command_interval,
                               channel_class, prompt_pattern, method)


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
        return execute_ioslike_ssh(device=device, commands=commands,
                                   creds=creds, incremental=incremental,
                                   with_errors=with_errors, timeout=timeout,
                                   command_interval=command_interval)

    # Fallback to telnet if it's enabled
    elif settings.TELNET_ENABLED:
        log.msg('execute_ioslike: TELNET ENABLED for %s' % device.nodeName)
        return execute_ioslike_telnet(device=device, commands=commands,
                                      creds=creds, incremental=incremental,
                                      with_errors=with_errors, timeout=timeout,
                                      command_interval=command_interval,
                                      loginpw=loginpw, enablepw=enablepw)

    else:
        msg = 'Both SSH and telnet either failed or are disabled.'
        log.msg('[%s]' % device, msg)
        e = exceptions.ConnectionFailure(msg)
        return defer.fail(e)


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

    port = device.nodePort or settings.TELNET_PORT
    log.msg('Trying IOS-like scripting to %s:%s' % (device, port), debug=True)
    reactor.connectTCP(device.nodeName, port, factory)
    return d


def execute_async_pty_ssh(device, commands, creds=None, incremental=None,
                          with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                          command_interval=0, prompt_pattern=None):
    """
    Execute via SSH for a device that requires shell + pty-req.

    Please see `~trigger.twister.execute` for a full description of the
    arguments and how this works.
    """
    channel_class = TriggerSSHAsyncPtyChannel
    method = 'Async PTY'
    if prompt_pattern is None:
        prompt_pattern = device.vendor.prompt_pattern

    return execute_generic_ssh(device, commands, creds, incremental,
                               with_errors, timeout, command_interval,
                               channel_class, prompt_pattern, method)


def execute_ioslike_ssh(device, commands, creds=None, incremental=None,
                        with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                        command_interval=0):
    """
    Execute via SSH for IOS-like devices with some exceptions.

    Please see `~trigger.twister.execute` for a full description of the
    arguments and how this works.
    """
    assert device.is_ioslike()

    # Test if device requires shell + pty-req
    if device.requires_async_pty:
        return execute_async_pty_ssh(device, commands, creds, incremental,
                                     with_errors, timeout, command_interval)
    # Or fallback to generic
    else:
        method = 'IOS-like'
        return execute_generic_ssh(device, commands, creds, incremental,
                                   with_errors, timeout, command_interval,
                                   method=method)


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

    channel_class = TriggerSSHGenericChannel
    method = 'NetScreen'
    prompt_pattern = settings.PROMPT_PATTERNS['netscreen']  # This sucks
    return execute_generic_ssh(device, commands, creds, incremental,
                               with_errors, timeout, command_interval,
                               channel_class, method=method,
                               prompt_pattern=prompt_pattern)


def execute_netscaler(device, commands, creds=None, incremental=None,
                      with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                      command_interval=0):
    """
    Execute commands on a NetScaler device.

    Please see `~trigger.twister.execute` for a full description of the
    arguments and how this works.
    """
    assert device.is_netscaler()

    channel_class = TriggerSSHNetscalerChannel
    method = 'NetScaler'
    return execute_generic_ssh(device, commands, creds, incremental,
                               with_errors, timeout, command_interval,
                               channel_class, method=method)


def execute_pica8(device, commands, creds=None, incremental=None,
                  with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                  command_interval=0):
    """
    Execute commands on a Pica8 device.  This is only needed to append
    '| no-more' to show commands because Pica8 currently (v2.2) lacks
    a global command to disable paging.

    Please see `~trigger.twister.execute` for a full description of the
    arguments and how this works.
    """
    assert device.is_pica8()

    channel_class = TriggerSSHPica8Channel
    method = 'Async PTY'
    return execute_generic_ssh(device, commands, creds, incremental,
                               with_errors, timeout, command_interval,
                               channel_class, method=method)

#  Classes
# ==================
#  Client Factories
# ==================


class TriggerClientFactory(protocol.ClientFactory, object):
    """
    Factory for all clients. Subclass me.
    """
    def __init__(self, deferred, creds=None, init_commands=None):
        self.d = deferred
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


class TriggerSSHChannelFactory(TriggerClientFactory):
    """
    Intended to be used as a parent of automated SSH channels (e.g. Junoscript,
    NetScreen, NetScaler) to eliminate boiler plate in those subclasses.
    """
    def __init__(self, deferred, commands, creds=None, incremental=None,
                 with_errors=False, timeout=None, channel_class=None,
                 command_interval=0, prompt_pattern=None, device=None,
                 connection_class=None):

        # Fallback to sane defaults if they aren't specified
        if channel_class is None:
            channel_class = TriggerSSHGenericChannel
        if connection_class is None:
            connection_class = TriggerSSHConnection
        if prompt_pattern is None:
            prompt_pattern = settings.DEFAULT_PROMPT_PAT

        self.protocol = TriggerSSHTransport
        self.display_banner = None
        self.commands = commands
        self.commanditer = iter(commands)
        self.initialized = False
        self.incremental = incremental
        self.with_errors = with_errors
        self.timeout = timeout
        self.channel_class = channel_class
        self.command_interval = command_interval
        self.prompt = re.compile(prompt_pattern)
        self.device = device
        self.connection_class = connection_class
        TriggerClientFactory.__init__(self, deferred, creds)

    def buildProtocol(self, addr):
        self.protocol = self.protocol()
        self.protocol.factory = self
        return self.protocol


class TriggerSSHPtyClientFactory(TriggerClientFactory):
    """
    Factory for an interactive SSH connection.

    'action' is a Protocol that will be connected to the session after login.
    Use it to interact with the user and pass along commands.
    """
    def __init__(self, deferred, action, creds=None, display_banner=None,
                 init_commands=None, device=None):
        self.protocol = TriggerSSHTransport
        self.action = action
        self.action.factory = self
        self.device = device
        self.display_banner = display_banner
        self.channel_class = TriggerSSHPtyChannel
        self.connection_class = TriggerSSHConnection
        self.commands = []
        self.command_interval = 0
        TriggerClientFactory.__init__(self, deferred, creds, init_commands)

# ==================
#  SSH Basics
# ==================


class TriggerSSHTransport(transport.SSHClientTransport, object):
    """
    SSH transport with Trigger's defaults.

    Call with magic factory attributes ``creds``, a tuple of login
    credentials, and ``connection_class``, the class of channel to open, and
    ``commands``, the list of commands to pass to the connection.
    """
    def verifyHostKey(self, pubKey, fingerprint):
        """Verify host key, but don't actually verify. Awesome."""
        return defer.succeed(True)

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
        transport.SSHClientTransport.dataReceived(self, data)

        # We have now seen the SSH version in the banner.
        # signal that the connection has been made successfully.
        if self.gotVersion and not preVersion:
            transport.SSHClientTransport.connectionMade(self)

    def connectionSecure(self):
        """Once we're secure, authenticate."""
        # The default SSHUserAuth requires options to be set.
        options = Options()
        options.identitys = None  # Let it use defaults
        options['noagent'] = None  # Use ssh-agent if SSH_AUTH_SOCK is set
        ua = TriggerSSHUserAuth(
            self.factory.creds.username, options,
            self.factory.connection_class(self.factory.commands)
        )
        self.requestService(ua)

    def receiveError(self, reason, desc):
        """Do this when we receive an error."""
        log.msg('Received an error, reason: %s, desc: %s)' % (reason, desc))
        self.sendDisconnect(reason, desc)

    def connectionLost(self, reason):
        """
        Detect when the transport connection is lost, such as when the
        remote end closes the connection prematurely (hosts.allow, etc.)
        """
        super(TriggerSSHTransport, self).connectionLost(reason)
        log.msg('Transport connection lost: %s' % reason.value)

    def sendDisconnect(self, reason, desc):
        """Trigger disconnect of the transport."""
        log.msg('Got disconnect request, reason: '
                '%r, desc: %r' % (reason, desc))

        # Only throw an error if this wasn't user-initiated (reason: 10)
        if reason == transport.DISCONNECT_CONNECTION_LOST:
            pass
        # Protocol errors should result in login failures
        elif reason == transport.DISCONNECT_PROTOCOL_ERROR:
            self.factory.err = exceptions.LoginFailure(desc)
        # Fallback to connection lost
        else:
            # Emulate the most common OpenSSH reason for this to happen
            if reason == transport.DISCONNECT_HOST_NOT_ALLOWED_TO_CONNECT:
                desc = ('ssh_exchange_identification: '
                        'Connection closed by remote host')
            self.factory.err = exceptions.SSHConnectionLost(reason, desc)

        super(TriggerSSHTransport, self).sendDisconnect(reason, desc)


class TriggerSSHUserAuth(SSHUserAuthClient):
    """Perform user authentication over SSH."""
    # The preferred order in which SSH authentication methods are tried.
    preferredOrder = settings.SSH_AUTHENTICATION_ORDER

    def getPassword(self, prompt=None):
        """Send along the password."""
        log.msg('Performing password authentication', debug=True)
        return defer.succeed(self.transport.factory.creds.password)

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
                response[idx] = self.transport.factory.creds.password

        return defer.succeed(response)

    def ssh_USERAUTH_BANNER(self, packet):
        """Display SSH banner."""
        if self.transport.factory.display_banner:
            banner, language = common.getNS(packet)
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


class TriggerSSHConnection(SSHConnection, object):
    """
    Used to manage, you know, an SSH connection.

    Optionally takes a list of commands that may be passed on.
    """
    def __init__(self, commands=None, *args, **kwargs):
        super(TriggerSSHConnection, self).__init__()
        self.commands = commands

    def serviceStarted(self):
        """Open the channel once we start."""
        log.msg('channel = %r' % self.transport.factory.channel_class)
        self.channel_class = self.transport.factory.channel_class
        self.command_interval = self.transport.factory.command_interval
        self.transport.factory.connection_success(self, self.transport)

        # Abstracted out so we can do custom stuff with self.openChannel
        self._channelOpener()

    def _channelOpener(self):
        """This is what calls ``self.channelOpen()``"""
        # Default behavior: Single channel/conn
        self.openChannel(self.channel_class(conn=self))

    def channelClosed(self, channel):
        """
        Forcefully close the transport connection when a channel closes
        connection. This is assuming only one channel is open.
        """
        log.msg('Forcefully closing transport connection!')
        self.transport.loseConnection()


class TriggerSSHMultiplexConnection(TriggerSSHConnection):
    """
    Used for multiplexing SSH 'exec' channels on a single connection.

    Opens a new channel for each command in the stack once the previous channel
    has closed. In this pattern the Connection and the Channel are intertwined.
    """
    def _channelOpener(self):
        log.msg('Multiplex connection started')
        self.work = list(self.commands)  # Make sure this is a list :)
        self.send_command()

    def channelClosed(self, channel):
        """
        Close the channel when we're done. But not the transport connection
        """
        log.msg('CHANNEL %s closed' % channel.id)
        SSHConnection.channelClosed(self, channel)

    def send_command(self):
        """
        Send the next command in the stack once the previous channel has closed
        """
        try:
            command = self.work.pop(0)
        except IndexError:
            log.msg('ALL COMMANDS HAVE FINISHED!')
            return None

        def command_completed(result, chan):
            log.msg('Command completed: %r' % chan.command)
            return result

        def command_failed(failure, chan):
            log.msg('Command failed: %r' % chan.command)
            return failure

        def log_status(result):
            log.msg('COMMANDS LEN: %s' % len(self.commands))
            log.msg(' RESULTS LEN: %s' % len(self.transport.factory.results))
            return result

        log.msg('SENDING NEXT COMMAND: %s' % command)

        # Send the command to the channel
        chan = self.channel_class(command, conn=self)

        d = defer.Deferred()
        reactor.callLater(
            self.command_interval, d.callback, self.openChannel(chan)
        )
        d.addCallback(command_completed, chan)
        d.addErrback(command_failed, chan)
        d.addBoth(log_status)
        return d

# ==================
#  SSH PTY Stuff
# ==================


class Interactor(protocol.Protocol):
    """
    Creates an interactive shell.

    Intended for use as an action with pty_connect(). See gong for an example.
    """
    def __init__(self, log_to=None):
        self._log_to = log_to
        self.enable_prompt = re.compile(settings.IOSLIKE_ENABLE_PAT)
        self.enabled = False
        self.initialized = False

    def _log(self, data):
        if self._log_to is not None:
            self._log_to.write(data)

    def connectionMade(self):
        """Fire up stdin/stdout once we connect."""
        c = protocol.Protocol()
        c.dataReceived = self.write
        self.stdio = stdio.StandardIO(c)
        self.device = self.factory.device  # Attach the device object
        self.prompt = re.compile(self.device.vendor.prompt_pattern)

    def loseConnection(self):
        """
        Terminate the connection. Link this to the transport method of the same
        name.
        """
        log.msg('[%s] Forcefully closing transport connection' % self.device)
        self.factory.transport.loseConnection()

    def dataReceived(self, data):
        """And write data to the terminal."""
        # -- Left during debugging. Enable on ASA not fixed here yet -- #
        # [2015-08-23] Think this isn't needed, keeping for reference?
        # log.msg('[%s] DATA: %r' % (self.device, data))
        # if requires_enable(self, data):
        #     log.msg('[%s] Device Requires Enable: %s' % (
        #         self.device,
        #         requires_enable(self, data)))
        #     log.msg('[%s] Is Device Currently Enabled: %s' % (
        #         self.device,
        #         self.enabled))

        # Check whether we need to send an enable password.
        if not self.enabled and requires_enable(self, data):
            log.msg('[%s] '
                    'Interactive PTY requires enable commands' % self.device)
            send_enable(self, disconnect_on_fail=False)  # Don't exit on fail

        # Setup and run the initial commands, and also assume we're enabled
        if data and not self.initialized:
            # Wait for a prompt of some sort to become available before we send
            # init commands.
            if self.prompt.search(data):
                # log.msg('[%s] PROMPT MATCHED: %r' % (self.device, data))
                self.enabled = True  # Forcefully set enable
                self.factory._init_commands(protocol=self)
                self.initialized = True

        self._log(data)
        self.stdio.write(data)


class TriggerSSHPtyChannel(channel.SSHChannel):
    """
    Used by pty_connect() to turn up an interactive SSH pty channel.
    """
    name = 'session'

    def channelOpen(self, data):
        """Setup the terminal when the channel opens."""
        pr = session.packRequest_pty_req(settings.TERM_TYPE,
                                         self._get_window_size(), '')
        self.conn.sendRequest(self, 'pty-req', pr)
        self.conn.sendRequest(self, 'shell', '')
        signal.signal(signal.SIGWINCH, self._window_resized)

        # Pass control to the action.
        self.factory = self.conn.transport.factory
        action = self.factory.action
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

# ==================
#  SSH Channels
# ==================


class TriggerSSHChannelBase(channel.SSHChannel, TimeoutMixin, object):
    """
    Base class for SSH channels.

    The method self._setup_channelOpen() should be called by channelOpen() in
    the subclasses. Before you subclass, however, see if you can't just use
    TriggerSSHGenericChannel as-is!
    """
    name = 'session'

    def _setup_channelOpen(self):
        """
        Call me in your subclass in self.channelOpen()::

            def channelOpen(self, data):
                self._setup_channelOpen()
                self.conn.sendRequest(self, 'shell', '')
                # etc.
        """
        self.factory = self.conn.transport.factory
        self.commanditer = self.factory.commanditer
        self.results = self.factory.results
        self.with_errors = self.factory.with_errors
        self.incremental = self.factory.incremental
        self.command_interval = self.factory.command_interval
        self.prompt = self.factory.prompt
        self.setTimeout(self.factory.timeout)
        self.device = self.factory.device
        log.msg('[%s] COMMANDS: %r' % (self.device, self.factory.commands))
        self.data = ''
        self.initialized = self.factory.initialized
        self.startup_commands = copy.copy(self.device.startup_commands)
        log.msg('[%s] My startup commands: %r' % (self.device,
                                                  self.startup_commands))

        # For IOS-like devices that require 'enable'
        self.enable_prompt = re.compile(settings.IOSLIKE_ENABLE_PAT)
        self.enabled = False

    def channelOpen(self, data):
        """Do this when the channel opens."""
        self._setup_channelOpen()
        d = self.conn.sendRequest(self, 'shell', '', wantReply=True)
        d.addCallback(self._gotResponse)
        d.addErrback(self._ebShellOpen)

        # Don't call _send_next() here, since we (might) expect to see a
        # prompt, which will kick off initialization.

    def _gotResponse(self, response):
        """
        Potentially useful if you want to do something after the shell is
        initialized.

        If the shell never establishes, this won't be called.
        """
        log.msg('[%s] Got channel request response!' % self.device)

    def _ebShellOpen(self, reason):
        log.msg('[%s] Channel request failed: %s' % (self.device, reason))

    def dataReceived(self, bytes):
        """Do this when we receive data."""
        # Append to the data buffer
        self.data += bytes
        log.msg('[%s] BYTES: %r' % (self.device, bytes))
        # log.msg('BYTES: (left: %r, max: %r, bytes: %r, data: %r)' %
        #         (self.remoteWindowLeft, self.localMaxPacket, len(bytes),
        #          len(self.data)))

        # Keep going til you get a prompt match
        m = self.prompt.search(self.data)
        if not m:
            # Do we need to send an enable password?
            if not self.enabled and requires_enable(self, self.data):
                send_enable(self)
                return None

            # Check for confirmation prompts
            # If the prompt confirms set the index to the matched bytes
            if is_awaiting_confirmation(self.data):
                log.msg('[%s] Got confirmation prompt: '
                        '%r' % (self.device, self.data))
                prompt_idx = self.data.find(bytes)
            else:
                return None
        else:
            # Or just use the matched regex object...
            log.msg('[%s] STATE: buffer %r' % (self.device, self.data))
            log.msg('[%s] STATE: prompt %r' % (self.device, m.group()))
            prompt_idx = m.start()

        # Strip the prompt from the match result
        result = self.data[:prompt_idx]  # Cut the prompt out
        result = result[result.find('\n')+1:]  # Keep all from first newline
        log.msg('[%s] STATE: result %r' % (self.device, result))

        # Only keep the results once we've sent any startup_commands
        if self.initialized:
            self.results.append(result)

        # By default we're checking for IOS-like or Juniper errors because most
        # vendors # fall under this category.
        has_errors = (has_ioslike_error(result) or has_juniper_error(result))
        if has_errors and not self.with_errors:
            log.msg('[%s] Command failed: %r' % (self.device, result))
            self.factory.err = exceptions.CommandFailure(result)
            self.loseConnection()
            return None

        # Honor the command_interval and then send the next command
        else:
            if self.command_interval:
                log.msg('[%s] Waiting %s seconds before sending next command' %
                        (self.device, self.command_interval))
            self.data = ''  # Flush the buffer before next command
            reactor.callLater(self.command_interval, self._send_next)

    def _send_next(self):
        """Send the next command in the stack."""
        self.resetTimeout()  # Reset the timeout

        if not self.initialized:
            log.msg('[%s] Not initialized; sending startup commands' %
                    self.device)
            if self.startup_commands:
                next_init = self.startup_commands.pop(0)
                log.msg('[%s] Sending initialize command: %r' % (self.device,
                                                                 next_init))
                self.write(next_init.strip() + self.device.delimiter)
                return None
            else:
                log.msg('[%s] Successfully initialized for command execution' %
                        self.device)
                self.initialized = True
                self.enabled = True  # Disable further enable checks.

        if self.incremental:
            self.incremental(self.results)

        try:
            next_command = self.commanditer.next()
        except StopIteration:
            log.msg('[%s] CHANNEL: out of commands, closing connection...' %
                    self.device)
            self.loseConnection()
            return None

        if next_command is None:
            self.results.append(None)
            self._send_next()
        else:
            log.msg('[%s] Sending SSH command %r' % (self.device,
                                                     next_command))
            self.write(next_command + self.device.delimiter)

    def loseConnection(self):
        """
        Terminate the connection. Link this to the transport method of the same
        name.
        """
        log.msg('[%s] Forcefully closing transport connection' % self.device)
        self.conn.transport.loseConnection()

    def timeoutConnection(self):
        """
        Do this when the connection times out.
        """
        log.msg('[%s] Timed out while sending commands' % self.device)
        self.factory.err = exceptions.CommandTimeout('Timed out while sending '
                                                     'commands')
        self.loseConnection()

    def request_exit_status(self, data):
        status = struct.unpack('>L', data)[0]
        log.msg('[%s] Exit status: %s' % (self.device, status))


class TriggerSSHGenericChannel(TriggerSSHChannelBase):
    """
    An SSH channel using all of the Trigger defaults to interact with network
    devices that implement SSH without any tricks.

    Currently A10, Cisco, Brocade, NetScreen can simply use this. Nice!

    Before you create your own subclass, see if you can't use me as-is!
    """


class TriggerSSHAsyncPtyChannel(TriggerSSHChannelBase):
    """
    An SSH channel that requests a non-interactive pty intended for async
    usage.

    Some devices won't allow a shell without a pty, so we have to do a
    'pty-req'.

    This is distinctly different from ~trigger.twister.TriggerSSHPtyChannel`
    which is intended for interactive end-user sessions.
    """
    def channelOpen(self, data):
        self._setup_channelOpen()

        # Request a pty even tho we are not actually using one.
        pr = session.packRequest_pty_req(
            settings.TERM_TYPE, (80, 24, 0, 0), ''
        )
        self.conn.sendRequest(self, 'pty-req', pr)
        d = self.conn.sendRequest(self, 'shell', '', wantReply=True)
        d.addCallback(self._gotResponse)
        d.addErrback(self._ebShellOpen)


class TriggerSSHCommandChannel(TriggerSSHChannelBase):
    """
    Run SSH commands on a system using 'exec'

    This will multiplex channels over a single connection. Because of the
    nature of the multiplexing setup, the master list of commands is stored on
    the SSH connection, and the state of each command is stored within each
    individual channel which feeds its result back to the factory.
    """
    def __init__(self, command, *args, **kwargs):
        super(TriggerSSHCommandChannel, self).__init__(*args, **kwargs)
        self.command = command
        self.result = None
        self.data = ''

    def channelOpen(self, data):
        """Do this when the channel opens."""
        self._setup_channelOpen()
        log.msg('[%s] Channel was opened' % self.device)
        d = self.conn.sendRequest(self, 'exec', common.NS(self.command),
                                  wantReply=True)
        d.addCallback(self._gotResponse)
        d.addErrback(self._ebShellOpen)

    def _gotResponse(self, _):
        """
        If the shell never establishes, this won't be called.
        """
        log.msg('[%s] CHANNEL %s: Exec finished.' % (self.device, self.id))
        self.conn.sendEOF(self)

    def _ebShellOpen(self, reason):
        log.msg('[%s] CHANNEL %s: Channel request failed: %s' % (self.device,
                                                                 reason,
                                                                 self.id))

    def dataReceived(self, bytes):
        self.data += bytes
        # log.msg('BYTES INFO: (left: %r, max: %r, bytes: %r, data: %r)' %
        #         (self.remoteWindowLeft,
        #          self.localMaxPacket,
        #          len(bytes),
        #          len(self.data)))
        log.msg('[%s] BYTES RECV: %r' % (self.device, bytes))

    def eofReceived(self):
        log.msg('[%s] CHANNEL %s: EOF received.' % (self.device, self.id))
        result = self.data

        # By default we're checking for IOS-like errors because most vendors
        # fall under this category.
        if has_ioslike_error(result) and not self.with_errors:
            log.msg('[%s] Command failed: %r' % (self.device, result))
            self.factory.err = exceptions.CommandFailure(result)

        # Honor the command_interval and then send the next command
        else:
            self.result = result
            self.conn.transport.factory.results.append(self.result)
            self.send_next_command()

    def send_next_command(self):
        """Send the next command in the stack stored on the connection"""
        log.msg('[%s] CHANNEL %s: '
                'sending next command!' % (self.device, self.id))
        self.conn.send_command()

    def closeReceived(self):
        log.msg('[%s] CHANNEL %s: Close received.' % (self.device, self.id))
        self.loseConnection()

    def loseConnection(self):
        """Default loseConnection"""
        log.msg("[%s] LOSING CHANNEL CONNECTION" % self.device)
        channel.SSHChannel.loseConnection(self)

    def closed(self):
        log.msg('[%s] Channel %s closed' % (self.device, self.id))
        log.msg('[%s] CONN CHANNELS: %s' % (self.device,
                                            len(self.conn.channels)))

        # If we're out of channels, shut it down!
        if len(self.conn.transport.factory.results) == len(self.conn.commands):
            log.msg('[%s] RESULTS MATCHES COMMANDS SENT.' % self.device)
            self.conn.transport.loseConnection()

    def request_exit_status(self, data):
        exitStatus = int(struct.unpack('>L', data)[0])
        log.msg('[%s] Exit status: %s' % (self.device, exitStatus))


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
        self._setup_channelOpen()
        self.conn.sendRequest(self, 'exec', common.NS('junoscript'))
        _xml = '<?xml version="1.0" encoding="us-ascii"?>\n'
        # TODO (jathan): Make the release version dynamic at some point
        _xml += ('<'
                 'junoscript version="1.0" hostname="%s" release="7.6R2.9"'
                 '>\n') % socket.getfqdn()
        self.write(_xml)
        self.xmltb = IncrementalXMLTreeBuilder(self._endhandler)

        self._send_next()

    def dataReceived(self, data):
        """Do this when we receive data."""
        log.msg('[%s] BYTES: %r' % (self.device, data))
        self.xmltb.feed(data)

    def _send_next(self):
        """Send the next command in the stack."""
        self.resetTimeout()

        if self.incremental:
            self.incremental(self.results)

        try:
            next_command = self.commanditer.next()
            log.msg('[%s] COMMAND: next command %s' % (self.device,
                                                       next_command))

        except StopIteration:
            log.msg('[%s] CHANNEL: out of commands, closing connection...' %
                    self.device)
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
            return None  # hopefully it's interior to an <rpc-reply>
        self.results.append(tag)

        if has_junoscript_error(tag) and not self.with_errors:
            log.msg('[%s] Command failed: %r' % (self.device, tag))
            self.factory.err = exceptions.JunoscriptCommandFailure(tag)
            self.loseConnection()
            return None

        # Honor the command_interval and then send the next command in the
        # stack
        else:
            if self.command_interval:
                log.msg('[%s] Waiting %s seconds before sending next command' %
                        (self.device, self.command_interval))
            reactor.callLater(self.command_interval, self._send_next)


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
        log.msg('[%s] BYTES: %r' % (self.device, bytes))
        # log.msg('BYTES: (left: %r, max: %r, bytes: %r, data: %r)' %
        #        (self.remoteWindowLeft,
        #         self.localMaxPacket,
        #         len(bytes),
        #         len(self.data)))

        # We have to check for errors first, because a prompt is not returned
        # when an error is received like on other systems.
        if has_netscaler_error(self.data):
            err = self.data
            if not self.with_errors:
                log.msg('[%s] Command failed: %r' % (self.device, err))
                self.factory.err = exceptions.CommandFailure(err)
                self.loseConnection()
                return None
            else:
                self.results.append(err)
                self._send_next()

        m = self.prompt.search(self.data)
        if not m:
            # log.msg('STATE: prompt match failure', debug=True)
            return None
        log.msg('[%s] STATE: prompt %r' % (self.device, m.group()))

        result = self.data[:m.start()]  # Strip ' Done\n' from results.

        if self.initialized:
            self.results.append(result)

        if self.command_interval:
            log.msg('[%s] Waiting %s seconds before sending next command' %
                    (self.device, self.command_interval))
        reactor.callLater(self.command_interval, self._send_next)

PICA8_NO_MORE_COMMANDS = ['show']


class TriggerSSHPica8Channel(TriggerSSHAsyncPtyChannel):
    def _setup_commanditer(self, commands=None):
        """
        Munge our list of commands and overload self.commanditer to append
        " | no-more" to any "show" commands.
        """
        if commands is None:
            commands = self.factory.commands
        new_commands = []
        for command in commands:
            root = command.split(' ', 1)[0]  # get the root command
            if root in PICA8_NO_MORE_COMMANDS:
                command += ' | no-more'
            new_commands.append(command)
        self.commanditer = iter(new_commands)

    def channelOpen(self, data):
        """
        Override channel open, which is where commanditer is setup in the
        base class.
        """
        super(TriggerSSHPica8Channel, self).channelOpen(data)
        self._setup_commanditer()  # Replace self.commanditer with our version

# ==================
#  XML Stuff (for Junoscript)
# ==================


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

# ==================
#  Telnet Channels
# ==================


class TriggerTelnetClientFactory(TriggerClientFactory):
    """
    Factory for a telnet connection.
    """
    def __init__(self, deferred, action, creds=None, loginpw=None,
                 enablepw=None, init_commands=None, device=None):
        self.protocol = TriggerTelnet
        self.action = action
        self.loginpw = loginpw
        self.enablepw = os.getenv('TRIGGER_ENABLEPW', enablepw)
        self.device = device
        self.action.factory = self
        TriggerClientFactory.__init__(self, deferred, creds, init_commands)


class TriggerTelnet(
        telnet.Telnet,
        telnet.ProtocolTransportMixin,
        TimeoutMixin):
    """
    Telnet-based session login state machine. Primarily used by IOS-like type
    devices.
    """
    def __init__(self, timeout=settings.TELNET_TIMEOUT):
        self.protocol = telnet.TelnetProtocol()
        self.waiting_for = [
            ('Username: ', self.state_username),                   # Most
            ('Please Enter Login Name  : ', self.state_username),  # OLD Fndry
            ('User Name:', self.state_username),                   # Dell
            ('login: ', self.state_username),                      # EOS, JunOs
            ('Password: ', self.state_login_pw),
        ]
        self.data = ''
        self.applicationDataReceived = self.login_state_machine
        self.timeout = timeout
        self.setTimeout(self.timeout)
        telnet.Telnet.__init__(self)

    def enableRemote(self, option):
        """
        Allow telnet clients to enable options if for some reason they aren't
        enabled already (e.g. ECHO). (Ref: http://bit.ly/wkFZFg) For some
        reason Arista Networks hardware is the only vendor that needs this
        method right now.
        """
        # log.msg('[%s] enableRemote option: %r' % (self.host, option))
        log.msg('enableRemote option: %r' % option)
        return True

    def login_state_machine(self, bytes):
        """Track user login state."""
        self.host = self.transport.connector.host
        log.msg('[%s] CONNECTOR HOST: %s' % (self.host,
                                             self.transport.connector.host))
        self.data += bytes
        log.msg('[%s] STATE:  got data %r' % (self.host, self.data))
        for (text, next_state) in self.waiting_for:
            log.msg('[%s] STATE:  possible matches %r' % (self.host, text))
            if self.data.endswith(text):
                log.msg('[%s] Entering state %r' % (self.host,
                                                    next_state.__name__))
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
            ('> ', self.state_logged_in),              # Juniper
            ('\n% ', self.state_percent_error),
            ('# ', self.state_logged_in),              # Dell
            ('\nUsername: ', self.state_raise_error),  # Cisco
            ('\nlogin: ', self.state_raise_error),     # Arista, Juniper
        ]

    def state_logged_in(self):
        """
        Once we're logged in, exit state machine and pass control to the
        action.
        """
        self.setTimeout(None)
        data = self.data.lstrip('\n')
        log.msg('[%s] state_logged_in, DATA: %r' % (self.host, data))
        del self.waiting_for, self.data

        # Run init_commands
        self.factory._init_commands(protocol=self)  # We are the protocol

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
        log.msg("[%s] ENABLE: Sending command: enable" % self.host)
        self.write('enable\n')
        self.waiting_for = [
            ('Password: ', self.state_enable_pw),  # Foundry
            ('Password:', self.state_enable_pw),   # Dell
        ]

    def state_login_pw(self):
        """Pass the login password from the factory or NetDevices"""
        if self.factory.loginpw:
            pw = self.factory.loginpw
        else:
            from trigger.netdevices import NetDevices
            pw = NetDevices().find(self.host).loginPW

        # Workaround to avoid TypeError when concatenating 'NoneType' and
        # 'str'. This *should* result in a LoginFailure.
        if pw is None:
            pw = ''

        # log.msg('Sending password %s' % pw)
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
            pw = NetDevices().find(self.host).enablePW
        # log.msg('Sending password %s' % pw)
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
        log.msg('Failed logging into %s' % self.transport.connector.host)
        self.factory.err = exceptions.LoginFailure('%r' % self.data.rstrip())
        self.loseConnection()

    def timeoutConnection(self):
        """Do this when we timeout logging in."""
        log.msg('[%s] '
                'Timed out while logging in' % self.transport.connector.host)
        self.factory.err = exceptions.LoginTimeout('Timed out while '
                                                   'logging in')
        self.loseConnection()


class IoslikeSendExpect(protocol.Protocol, TimeoutMixin):
    """
    Action for use with TriggerTelnet as a state machine.

    Take a list of commands, and send them to the device until we run out or
    one errors. Wait for a prompt after each.
    """
    def __init__(self, device, commands, incremental=None, with_errors=False,
                 timeout=None, command_interval=0):
        self.device = device
        self._commands = commands
        self.commanditer = iter(commands)
        self.incremental = incremental
        self.with_errors = with_errors
        self.timeout = timeout
        self.command_interval = command_interval
        self.prompt = re.compile(settings.IOSLIKE_PROMPT_PAT)
        self.startup_commands = copy.copy(self.device.startup_commands)
        log.msg('[%s] My initialize commands: %r' % (self.device,
                                                     self.startup_commands))
        self.initialized = False

    def connectionMade(self):
        """Do this when we connect."""
        self.setTimeout(self.timeout)
        self.results = self.factory.results = []
        self.data = ''
        log.msg('[%s] connectionMade, data: %r' % (self.device, self.data))

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
            self.loseConnection()
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
                self.write(next_init.strip() + self.device.delimiter)
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
            self.loseConnection()
            return None

        if next_command is None:
            self.results.append(None)
            self._send_next()
        else:
            log.msg('[%s] Sending command %r' % (self.device, next_command))
            self.write(next_command + self.device.delimiter)

    def timeoutConnection(self):
        """Do this when we timeout."""
        log.msg('[%s] Timed out while sending commands' % self.device)
        self.factory.err = exceptions.CommandTimeout('Timed out while '
                                                     'sending commands')
        self.loseConnection()
