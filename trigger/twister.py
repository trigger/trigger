# -*- coding: utf-8 -*-

"""
Login and basic command-line interaction support using the Twisted asynchronous
I/O framework. The Trigger Twister is just like the Mersenne Twister, except not at all.
"""

__author__ = 'Jathan McCollum, Eileen Tschetter, Mark Thomas, Michael Shields'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2006-2011, AOL Inc.'

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
from twisted.conch.ssh.transport import DISCONNECT_CONNECTION_LOST
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
from trigger.netdevices import NetDevices
import trigger.tacacsrc as tacacsrc
from trigger.utils.network import ping

# Dump all logging to stdout if we run 'python -O'
if not __debug__:
    log.startLogging(sys.stdout)


# Exceptions
class TriggerTwisterError(Exception): pass
class LoginFailure(TriggerTwisterError): pass
class LoginTimeout(LoginFailure): pass
class CommandTimeout(TriggerTwisterError): pass
class CommandFailure(TriggerTwisterError): pass
class IoslikeCommandFailure(CommandFailure): pass
class NetscalerCommandFailure(CommandFailure): pass

class SSHConnectionLost(TriggerTwisterError):
    def __init__(self, code, desc):
        self.code = code
        TriggerTwisterError.__init__(self, desc)

class JunoscriptCommandFailure(CommandFailure):
    def __init__(self, tag):
        self.tag = tag

    def __str__(self):
        s = 'JunOS XML command failure:\n'
        ns = '{http://xml.juniper.net/xnm/1.1/xnm}'
        for e in self.tag.findall('.//%serror' % ns):
            for e2 in e:
                s += '  %s: %s\n' % (e2.tag.replace(ns, ''), e2.text)
        return s


# Functions
def has_junoscript_error(tag):
    """Test whether an Element contains a Junoscript xnm:error."""
    #if ElementTree(tag).find('//{http://xml.juniper.net/xnm/1.1/xnm}error'):
    if ElementTree(tag).find('.//{http://xml.juniper.net/xnm/1.1/xnm}error'):
        return True
    return False

def has_ioslike_error(s):
    """Test whether a string seems to contain an IOS error."""
    return s.startswith('%') or '\n%' in s

def has_netscaler_error(s):
    """Test whether a string seems to contain a NetScaler error."""
    return s.startswith('ERROR:')

def pty_connect(device, action, creds=None, display_banner=None, ping_test=False):
    """
    Connect to a device and log in.  Use SSHv2 or telnet as appropriate.

    @device is a trigger.netdevices.NetDevice object.

    @action is a Protocol object (not class) that will be activated when
    the session is ready.

    @creds is a (username, password) tuple.  By default, .tacacsrc AOL
    credentials will be used. Override that here.

    @display_banner will be called for SSH pre-authentication banners.
    It will receive two args, 'banner' and 'language'.  By default,
    nothing will be done with the banner.

    @ping_test is a boolean that causes a ping to be performed. If True, ping must
    succeed in order to proceed.
    """
    d = defer.Deferred()

    # Only proceed if ping succeeds
    if ping_test:
        log.msg('Pinging %s' % device, debug=True)
        if not ping(device.nodeName):
            log.msg('Ping to %s failed' % device, debug=True)
            return None

    # SSH?
    log.msg('SSH TYPES: %s' % settings.SSH_TYPES, debug=True)
    if device.manufacturer in settings.SSH_TYPES:
        if hasattr(sys, 'ps1') or not sys.stderr.isatty() \
         or not sys.stdin.isatty() or not sys.stdout.isatty():
            # Shell not in interactive mode.
            pass
            
        else:
            if not creds and device.is_firewall():
                creds = tacacsrc.get_device_password(str(device))

        factory = TriggerSSHPtyClientFactory(d, action, creds, display_banner)
        log.msg('Trying SSH to %s' % device, debug=True)
        reactor.connectTCP(device.nodeName, 22, factory)

    # or Telnet?
    else:
        factory = TriggerTelnetClientFactory(d, action, creds)
        log.msg('Trying telnet to %s' % device, debug=True)
        reactor.connectTCP(device.nodeName, 23, factory)

    return d

def execute_junoscript(device, commands, creds=None, incremental=None,
        with_errors=False, timeout=settings.DEFAULT_TIMEOUT):
    """
    Connect to a Juniper and enable XML mode.  Sequentially execute
    all the XML commands in the iterable 'commands' (ElementTree.Element
    objects suitable for wrapping in <rpc>).  Returns a deferred,
    whose callback will get a sequence of all the XML results after
    the connection is finished.

    If any command returns xnm:error, the connection is dropped
    immediately and the errback will fire with the failed command; or,
    set 'with_errors' to get the exception objects in the list instead.
    Connection failures will still fire the errback.

    Any None object in the command sequence will result in a None being
    placed in the output sequence, with no command issued to the router.

    @incremental (optional) will be called with an empty sequence 
    immediately on connecting, and each time a result comes back with 
    the list of all results.

    @commands is usually just a list.  However, you can have also
    make it a generator, and have it and @incremental share a closure to
    some state variables.  This allows you to determine what commands
    to execute dynamically based on the results of previous commands.
    This implementation is experimental and it might be a better idea
    to have the 'incremental' callback determine what command to execute
    next; it could then be a method of an object that keeps state.

        BEWARE: Your generator cannot block; you must immediately 
        decide what next command to execute, if any.
    
    @timeout is the command timeout in seconds or None to disable.
    The default is in settings.DEFAULT_TIMEOUT; CommandTimeout errors
    will result if a command seems to take longer than that to run.
    LoginTimeout errors are always possible and cannot be disabled.
    """

    assert device.manufacturer == 'JUNIPER'
    d = defer.Deferred()
    channel = TriggerSSHJunoscriptChannel
    factory = TriggerSSHChannelFactory(d, commands, creds, incremental,
                                      with_errors, timeout, channel,
                                      command_interval=0)

    log.msg('Trying Junoscript SSH to %s' % device, debug=True)
    reactor.connectTCP(device.nodeName, 22, factory)
    return d

def execute_ioslike(device, commands, creds=None, incremental=None,
                    with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                    loginpw=None, enablepw=None, command_interval=0):
    """
    Connect to a Cisco/IOS-like device over telnet. See execute_junoscript().
    """

    # TODO (jathan): This execute function should support SSH.
    assert device.manufacturer in settings.IOSLIKE_VENDORS

    d = defer.Deferred()
    action = IoslikeSendExpect(device, commands, incremental, with_errors,
                               timeout, command_interval)
    factory = TriggerTelnetClientFactory(d, action, creds, loginpw, enablepw)

    log.msg('Trying IOS-like scripting to %s' % device, debug=True)
    reactor.connectTCP(device.nodeName, 23, factory)
    return d

def execute_netscreen(device, commands, creds=None, incremental=None,
                      with_errors=False, timeout=settings.DEFAULT_TIMEOUT):
    """
    Connect to a NetScreen device. See execute_junoscript().
    """
    assert device.manufacturer in ('JUNIPER', 'NETSCREEN TECHNOLOGIES')
    assert device.is_firewall()

    if not creds:
        creds = tacacsrc.get_device_password(str(device))

    d = defer.Deferred()
    channel = TriggerSSHNetscreenChannel
    factory = TriggerSSHChannelFactory(d, commands, creds, incremental,
                                      with_errors, timeout, channel)

    log.msg('Trying Netscreen SSH to %s' % device, debug=True)
    reactor.connectTCP(device.nodeName, 22, factory)
    return d

def execute_netscaler(device, commands, creds=None, incremental=None,
                      with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                      command_interval=0):
    """
    Connect to a NetScaler device. See execute_junoscript().
    """
    assert device.is_netscaler()

    d = defer.Deferred()
    channel = TriggerSSHNetscalerChannel
    factory = TriggerSSHChannelFactory(d, commands, creds, incremental,
                                      with_errors, timeout, channel,
                                      command_interval)

    log.msg('Trying NetScaler SSH to %s' % device, debug=True)
    reactor.connectTCP(device.nodeName, 22, factory)
    return d


# Classes
#==================
# Client Basics
#==================
class TriggerClientFactory(ClientFactory):
    """
    Factory for all clients. Subclass me.
    """

    def __init__(self, deferred, creds=None):
        self.d = deferred
        self.creds = creds or tacacsrc.Tacacsrc().creds['aol']
        self.results = self.err = None

    def clientConnectionFailed(self, connector, reason):
        """Do this when the connection fails."""
        self.d.errback(reason)

    def clientConnectionLost(self, connector, reason):
        """Do this when the connection is lost."""
        log.msg('Client connection lost', debug=True)
        if self.err:
            self.d.errback(self.err)
        else:
            self.d.callback(self.results)

class TriggerSSHTransport(SSHClientTransport, object):
    """
    Call with magic factory attributes 'creds', a tuple of login
    credentials, and 'channel', the class of channel to open.
    """

    def verifyHostKey(self, pubKey, fingerprint):
        """Verify host key, but don't actually verify. Awesome."""
        return defer.succeed(1)

    def connectionSecure(self):
        """Once we're secure, authenticate."""
        self.requestService(TriggerSSHUserAuth(
                self.factory.creds[0], TriggerSSHConnection()))

    def receiveError(self, reason, desc):
        """Do this when we receive an error."""
        self.sendDisconnect(reason, desc)

    def sendDisconnect(self, reason, desc):
        """Trigger disconnect of the transport."""
        if reason != DISCONNECT_CONNECTION_LOST:
            self.factory.err = SSHConnectionLost(reason, desc)
        super(TriggerSSHTransport, self).sendDisconnect(reason, desc)

class TriggerSSHUserAuth(SSHUserAuthClient):
    """Perform user authentication over SSH."""
    # Only try one authentication mechanism.
    preferredOrder = ['password']

    def getPassword(self, prompt=None):
        """Send along the password."""
        #self.getPassword()
        log.msg('Performing password authentication', debug=True)
        return defer.succeed(self.transport.factory.creds[1])

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
                log.msg("Got password prompt: %r, sending password!" % prompt, debug=True)
                response[idx] = self.transport.factory.creds[1]

        return defer.succeed(response)

    def ssh_USERAUTH_BANNER(self, packet):
        """Display SSH banner."""
        if self.transport.factory.display_banner:
            banner, language = getNS(packet)
            self.transport.factory.display_banner(banner, language)

class TriggerSSHConnection(SSHConnection, object):
    """Used to manage, you know, an SSH connection."""

    def serviceStarted(self):
        """Open the channel once we start."""
        self.openChannel(self.transport.factory.channel(conn=self))

    def channelClosed(self, channel):
        """Close the channel when we're done."""
        self.transport.loseConnection()

#==================
# SSH PTY Stuff
#==================
class Interactor(Protocol):
    """
    Creates an interactive shell. Intended for use as an action with pty_connect(). 
    See gong for an example.
    """

    def connectionMade(self):
        """Fire up stdin/stdout once we connect."""
        c = Protocol()
        c.dataReceived = self.write
        self.stdio = stdio.StandardIO(c)

    def dataReceived(self, data):
        """And write data to the terminal."""
        log.msg('Interactor.dataReceived: %r' % data, debug=True)
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
    Factory for an interactive SSH connection.  'action' is a Protocol
    that will be connected to the session after login.  Use it to interact
    with the user and pass along commands.
    """

    def __init__(self, deferred, action, creds=None, display_banner=None):
        self.protocol = TriggerSSHTransport
        self.action = action
        self.action.factory = self
        self.display_banner = display_banner
        self.channel = TriggerSSHPtyChannel
        TriggerClientFactory.__init__(self, deferred, creds)

#==================
# XML Stuff
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
# SSH Channels
#==================
class TriggerSSHChannelFactory(TriggerClientFactory):
    """
    Intended to be used as a parent of automated SSH channels (e.g. Junoscript,
    NetScreen, NetScaler) to eliminate boiler plate in those subclasses.
    """

    def __init__(self, deferred, commands, creds=None, incremental=None,
            with_errors=False, timeout=None, channel=None, command_interval=0):
        if channel is None:
            raise TriggerTwisterError('You must specify an SSH channel class')

        self.protocol = TriggerSSHTransport
        self.display_banner = None
        self.commands = commands
        self.incremental = incremental
        self.with_errors = with_errors
        self.timeout = timeout
        self.channel = channel
        self.command_interval = command_interval
        TriggerClientFactory.__init__(self, deferred, creds)

class TriggerSSHChannelBase(SSHChannel, TimeoutMixin):
    """
    Base class for SSH Channels. setup_channelOpen() should be called by
    channelOpen() in the child class
    ."""
    name = 'session'

    def setup_channelOpen(self, data):
        """
        Call me in your subclass in self.channelOpen()::

            def channelOpen(self, data):
                self.setup_channelOpen(data)
                self.conn.sendRequest(self, 'shell', '')
                # etc.
        """
        self.factory = self.conn.transport.factory
        self.commanditer = iter(self.factory.commands)
        self.results = self.factory.results = []
        self.with_errors = self.factory.with_errors
        self.incremental = self.factory.incremental
        self.command_interval = self.factory.command_interval
        self.setTimeout(self.factory.timeout)

    def loseConnection(self):
        """
        Terminate the connectoin. Link this to the transport method
        of the same name
        """
        self.conn.transport.loseConnection()

    def timeoutConnection(self):
        """
        Do this when the connection times out.
        """
        self.factory.err = CommandTimeout('Timed out while sending commands')
        self.loseConnection()

class TriggerSSHJunoscriptChannel(TriggerSSHChannelBase):
    """
    Run Junoscript commands on a Juniper router.  This completely assumes 
    that we are the only channel in the factory (a TriggerJunoscriptFactory) 
    and walks all the way back up to the factory for its arguments.
    """

    def channelOpen(self, data):
        """Do this when channel opens."""
        self.setup_channelOpen(data)
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
        #log.msg('CHANNEL: timeout=%s' % self.factory.timeout, debug=True)

        if self.incremental:
            self.incremental(self.results)

        try:
            next = self.commanditer.next()
            log.msg('COMMAND: next command=%s' % next, debug=True)

        except StopIteration:
            log.msg('CHANNEL: out of commands, closing...', debug=True)
            self.loseConnection()
            return None

        if next is None:
            self.results.append(None)
            self._send_next()
        else:
            rpc = Element('rpc')
            rpc.append(next)
            ElementTree(rpc).write(self)

    def _endhandler(self, tag):
        """Do this when the XML stream ends."""
        if tag.tag != '{http://xml.juniper.net/xnm/1.1/xnm}rpc-reply':
            return  None # hopefully it's interior to an <rpc-reply>
        self.results.append(tag)
        if has_junoscript_error(tag) and not self.with_errors:
            self.factory.err = JunoscriptCommandFailure(tag)
            self.loseConnection()
            return None
        else:
            self._send_next()

class TriggerSSHNetscalerChannel(TriggerSSHChannelBase):
    """
    Same as TriggerSSHJunoscriptChannel but for NetScreen. Mostly
    copy-pasted, and probably needs refactoring but it works.
    """

    def channelOpen(self, data):
        """Do this when channel opens."""
        self.setup_channelOpen(data)
        self.initialized = False
        self.data = ''
        self.prompt = re.compile('\sDone\n$') # ' Done \n'  only
        self.conn.sendRequest(self, 'shell', '')
        self.initialize = [] # A command to run at startup e.g. ['enable\n']

        # Don't call _send_next(), since we expect to see a prompt, which
        # will kick off initialization.

    def dataReceived(self, bytes):
        """Do this when we receive data."""
        self.data += bytes
        log.msg('BYTES: %r' % bytes, debug=True)
        log.msg('BYTES: (left: %r, max: %r, bytes: %r, data: %r)' % 
                (self.remoteWindowLeft, self.localMaxPacket, len(bytes), len(self.data)))

        # We have to check for errors first, because a prompt is not returned
        # when an error is received like on other systems. 
        if has_netscaler_error(self.data):
            err = self.data
            if not self.with_errors:
                self.factory.err = NetscalerCommandFailure(err)
                self.loseConnection()
                return None
            else:
                self.results.append(err)
                self._send_next()

        m = self.prompt.search(self.data)
        if not m:
            log.msg('STATE: prompt match failure', debug=True)
            return None
        log.msg('STATE: prompt %r' % m.group(), debug=True)

        result = self.data[:m.start()] # Strip ' Done\n' from results.

        if self.initialized:
            self.results.append(result)

        if self.command_interval > 0:
            time.sleep(self.command_interval)

        self._send_next()

    def _send_next(self):
        """Send the next command in the stack."""
        self.data = ''
        self.resetTimeout()

        if not self.initialized:
            if self.initialize:
                self.write(self.initialize.pop(0))
                return None
            else:
                self.initialized = True

        if self.incremental:
            self.incremental(self.results)

        try:
            next = self.commanditer.next()
        except StopIteration:
            log.msg('CHANNEL: out of commands, closing...', debug=True)
            self.loseConnection()
            return None

        if next is None:
            self.results.append(None)
            self._send_next()
        else:
            log.msg('sending NetScaler command: %r' % next, debug=True)
            self.write(next + '\n')

class TriggerSSHNetscreenChannel(TriggerSSHChannelBase):
    """
    An SSH Channel to interact with NetScreens (running ScreenOS).
    """
    name = 'session'

    def channelOpen(self, data):
        """Do this when the channel opens."""
        self.setup_channelOpen(data)
        self.initialized = False
        self.data = ''
        self.prompt = re.compile('(\w+?:|)[\w().-]*\(?([\w.-])?\)?\s*->\s*$')
        self.conn.sendRequest(self, 'shell', '')
        
    def dataReceived(self, bytes):
        """Do this when we receive data."""
        self.data += bytes

        m = self.prompt.search(self.data)
        if not m:
            return None

        result = self.data[:m.start()]
        result = result[result.find('\n')+1:]

        if self.initialized:
            self.results.append(result)

        self._send_next()

    def _send_next(self):
        """Send the next command in the stack."""
        self.data = ''
        if not self.initialized:
            self.initialized = True

        if self.incremental:
            self.incremental(self.results)

        try:
            next = self.commanditer.next()
        except StopIteration:
            self.loseConnection()
            return None
        if next is None:
            self.results.append(None)
            self._send_next()
        else:
            log.msg('sending Netscreen command %s' % next, debug=True)
            self.write(next + '\n')

#==================
# Telnet Channels
#==================
class TriggerTelnetClientFactory(TriggerClientFactory):
    """
    Factory for a telnet connection.
    """

    def __init__(self, deferred, action, creds=None, loginpw=None, enablepw=None):
        self.protocol = TriggerTelnet
        self.action = action
        self.loginpw = loginpw
        self.enablepw = enablepw
        self.action.factory = self
        TriggerClientFactory.__init__(self, deferred, creds)

class TriggerTelnet(Telnet, ProtocolTransportMixin, TimeoutMixin):
    """
    Telnet-based session. Primarily used by IOS-like type devices.
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
        self.write(self.factory.creds[0] + '\n')
        self.waiting_for = [
            ('Password: ', self.state_password),
            ('Password:', self.state_password),  # Dell
        ]

    def state_password(self):
        """After we got password prompt, check for enable prompt."""
        self.write(self.factory.creds[1] + '\n')
        self.waiting_for = [
            ('#', self.state_logged_in),
            ('>', self.state_enable),
            ('> ', self.state_logged_in),        # Juniper
            ('\n% ', self.state_percent_error),
            ('# ', self.state_logged_in),        # Dell
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
            pw = NetDevices().find(self.transport.connector.host).loginPW
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
        self.factory.err = LoginFailure('Login failed: %s' % self.data.rstrip())
        self.loseConnection()

    def timeoutConnection(self):
        """Do this when we timeout logging in."""
        self.factory.err = LoginTimeout('Timed out while logging in')
        self.loseConnection()

class IoslikeSendExpect(Protocol, TimeoutMixin):
    """
    Action for use with TriggerTelnet. Take a list of commands, and send them
    to the device until we run out or one errors. Wait for a prompt after each.
    """

    def __init__(self, dev, commands, incremental=None, with_errors=False,
                 timeout=None, command_interval=0):
        self.dev = dev
        self.commanditer = iter(commands)
        self.incremental = incremental
        self.with_errors = with_errors
        self.timeout = timeout
        self.command_interval = command_interval

        # Match prompt for IOS-like in (config), (config-if), (config-line).
        #self.prompt =  re.compile('^[a-zA-Z0-9-_]+(@[a-zA-Z0-9-_]+)?(\(config(-[a-z]+)?\))?#', re.M)
        self.prompt =  re.compile('[a-zA-Z0-9-_]+(@[a-zA-Z0-9-_]+)?(\(config(-[a-z]+)?\))?#', re.M)
        self.initialize = [{'CISCO SYSTEMS': 'terminal length 0\n',
                            'ARISTA NETWORKS': 'terminal length 0\n',
                            'FOUNDRY': 'skip-page-display\n',
                            'BROCADE': 'skip-page-display\n',
                            'DELL': 'terminal datadump\n',
                           }[dev.manufacturer]]
        log.msg('My initialize commands: %r' % self.initialize, debug=True)
        self.initialized = False

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
        m = self.prompt.search(self.data)
        if not m:
            return None

        result = self.data[:m.start()]
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
            log.msg('Got some kind of error: %r' % result, debug=True)
            self.factory.err = IoslikeCommandFailure(result)
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
        self.factory.err = CommandTimeout('Timed out while sending commands')
        self.loseConnection()
