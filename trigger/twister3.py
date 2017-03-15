# -*- coding: utf-8 -*-

"""
Login and basic command-line interaction support using the Twisted asynchronous
I/O framework. The Trigger Twister is just like the Mersenne Twister, except
not at all.
"""

from __future__ import absolute_import
import fcntl
import struct
import sys
import tty
from collections import deque
from twisted.conch.ssh import channel, common, session, transport
from twisted.internet import defer, protocol, reactor
from twisted.protocols.policies import TimeoutMixin
from twisted.python import log

from trigger.conf import settings
from trigger import exceptions

from twisted.conch.client.direct import SSHClientFactory
from twisted.conch.ssh import userauth
from twisted.conch.ssh import connection
from crochet import run_in_reactor, setup

setup()


def generate_endpoint(hostname, port, creds, prompt, has_error, delimiter,
                      options=None, verifyHostKey=None):
    """Generate Trigger endpoint for a given device.

    The purpose of this function is to generate endpoint clients for use by a `~trigger.netdevices.NetDevice` object.

    :param device: A string representing the devices' hostname.
    :param prompt: The prompt regexp used to synchronise the CLI session i/o.
    """
    if options is None:
        options = {'reconnect': False}

    return connect(hostname, port, options, verifyHostKey, creds, prompt,
                   has_error, delimiter).wait()


@run_in_reactor
def connect(hostname, port, options, verifyHostKey, creds, prompt, has_error,
            delimiter):
    """A generic connect function that runs within the crochet reactor."""
    d = defer.Deferred()
    factory = ClientFactory(d, hostname, options, verifyHostKey, creds, prompt,
                            has_error, delimiter)
    reactor.connectTCP(hostname, port, factory)
    return d


class ClientFactory(SSHClientFactory):
    """Client factory responsible for standing up an SSH session.
    """
    def __init__(self, d, hostname, options, verifyHostKey,
                 creds, prompt, has_error, delimiter):
        self.d = d
        self.options = options
        self.verifyHostKey = verifyHostKey
        self.creds = creds
        self.hostname = hostname
        self.prompt = prompt
        self.has_error = has_error
        self.delimiter = delimiter

    def buildProtocol(self, addr):
        trans = ClientTransport(self)
        # if self.options['ciphers']:
            # trans.supportedCiphers = self.options['ciphers']
        # if self.options['macs']:
            # trans.supportedMACs = self.options['macs']
        # if self.options['compress']:
            # trans.supportedCompressions[0:1] = ['zlib']
        # if self.options['host-key-algorithms']:
            # trans.supportedPublicKeys = self.options['host-key-algorithms']
        return trans


class SendExpect(protocol.Protocol, TimeoutMixin):
    """
    Action for use with TriggerTelnet as a state machine.

    Take a list of commands, and send them to the device until we run out or
    one errors. Wait for a prompt after each.
    """
    def __init__(self):
        self.factory = None
        self.connected = False
        self.disconnect = False
        self.initialized = False
        self.prompt = None
        self.startup_commands = []
        self.command_interval = 1
        self.incremental = None
        self.on_error = defer.Deferred()
        self.todo = deque()
        self.done = None
        self.doneLock = defer.DeferredLock()

    def connectionMade(self):
        """Do this when we connect."""
        self.factory = self.transport.conn.transport.factory
        self.prompt = self.factory.prompt
        self.hostname = self.factory.hostname
        self.has_error = self.factory.has_error
        self.delimiter = self.factory.delimiter
        self.commands = []
        self.commanditer = iter(self.commands)
        self.connected = True
        self.finished = defer.Deferred()
        self.results = self.factory.results = []
        self.data = ''
        log.msg('[%s] connectionMade, data: %r' % (self.hostname, self.data))
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
        log.msg('[%s] BYTES: %r' % (self.hostname, bytes))
        self.data += bytes # See if the prompt matches, and if it doesn't, see if it is waiting
        # for more input (like a [y/n]) prompt), and continue, otherwise return
        # None
        m = self.prompt.search(self.data)
        if not m:
            # If the prompt confirms set the index to the matched bytes,
            def is_awaiting_confirmation(d):
                pass

            if is_awaiting_confirmation(self.data):
                log.msg('[%s] Got confirmation prompt: %r' % (self.hostname,
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
        log.msg('[%s] result BEFORE: %r' % (self.hostname, result))
        result = result[result.find('\n')+1:]
        log.msg('[%s] result AFTER: %r' % (self.hostname, result))

        if self.initialized:
            self.results.append(result)

        if self.has_error(result) and not self.with_errors:
            log.msg('[%s] Command failed: %r' % (self.hostname, result))
            self.factory.err = exceptions.CommandFailure(result)
        else:
            if self.command_interval:
                log.msg('[%s] Waiting %s seconds before sending next command' %
                        (self.hostname, self.command_interval))

            reactor.callLater(self.command_interval, self._send_next)

    def _send_next(self):
        """Send the next command in the stack."""
        self.data = ''
        self.resetTimeout()

        if not self.initialized:
            log.msg('[%s] Not initialized, sending startup commands' %
                    self.hostname)
            if self.startup_commands:
                next_init = self.startup_commands.pop(0)
                log.msg('[%s] Sending initialize command: %r' % (self.hostname,
                                                                 next_init))
                self.transport.write(next_init.strip() + self.delimiter)
                return None
            else:
                log.msg('[%s] Successfully initialized for command execution' %
                        self.hostname)
                self.initialized = True

        if self.incremental:
            self.incremental(self.results)

        try:
            next_command = self.commanditer.next()
        except StopIteration:
            log.msg('[%s] No more commands to send, moving on...' %
                    self.hostname)

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
            log.msg('[%s] Sending command %r' % (self.hostname, next_command))
            self.transport.write(next_command + '\n')

    def timeoutConnection(self):
        """Do this when we timeout."""
        log.msg('[%s] Timed out while sending commands' % self.hostname)
        self.factory.err = exceptions.CommandTimeout('Timed out while '
                                                     'sending commands')
        self.transport.loseConnection()

    def close(self):
        self.transport.loseConnection()


class SSHAsyncPtyChannel(channel.SSHChannel):
    """A generic SSH Pty Channel that connects to a simple SendExpect CLI Protocol.
    """
    name = "session"

    def openFailed(self, reason):
        """Channel failed handler."""
        self._commandConnected.errback(reason)

    def channelOpen(self, data):
        # Request a pty even tho we are not actually using one.
        self._commandConnected = self.conn.transport.factory.d
        pr = session.packRequest_pty_req(
            settings.TERM_TYPE, (80, 24, 0, 0), ''
        )
        self.conn.sendRequest(self, 'pty-req', pr)
        d = self.conn.sendRequest(self, 'shell', '', wantReply=True)
        d.addCallback(self._gotResponse)
        d.addErrback(self._ebShellOpen)

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
        # Might be an idea to use a protocol.Factory to generate the protocol instance
        # instead of hardcoding it.
        self._protocol = SendExpect()
        self._protocol.makeConnection(self)
        self._commandConnected.callback(self._protocol)

    def _gotResponse(self, response):
        """
        Potentially useful if you want to do something after the shell is
        initialized.

        If the shell never establishes, this won't be called.
        """
        log.msg('[%s] Got channel request response!' % 'blah')
        self._execSuccess(None)

    def _ebShellOpen(self, reason):
        log.msg('[%s] Channel request failed: %s' % ('bloh', reason))


    def dataReceived(self, data):
        """Callback for when data is received.

        Once data is received in the channel we defer to the protocol level dataReceived method.
        """
        self._protocol.dataReceived(data)
        # channel.SSHChannel.dataReceived(self, data)


class ClientConnection(connection.SSHConnection):

    def serviceStarted(self):
        self.openChannel(SSHAsyncPtyChannel(conn=self))


class ClientUserAuth(userauth.SSHUserAuthClient):
    """Perform user authentication over SSH."""
    # The preferred order in which SSH authentication methods are tried.
    preferredOrder = settings.SSH_AUTHENTICATION_ORDER

    def __init__(self, user, password, instance):
        self.user = user
        self.password = password
        self.instance = instance

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


class ClientTransport(transport.SSHClientTransport):
    def __init__(self, factory):
        self.factory = factory

    def verifyHostKey(self, pubKey, fingerprint):
        return defer.succeed(1)

    def connectionSecure(self):
        self.requestService(ClientUserAuth(self.factory.creds.username,
                                           self.factory.creds.password,
                                           ClientConnection()
                                           ))

    # def connectionMade(self):
        # """
        # Once the connection is up, set the ciphers but don't do anything else!
        # """
        # self.currentEncryptions = transport.SSHCiphers(
            # 'none', 'none', 'none', 'none'
        # )
        # self.currentEncryptions.setKeys('', '', '', '', '', '')

    # def dataReceived(self, data):
        # """
        # Explicity override version detection for edge cases where "SSH-"
        # isn't on the first line of incoming data.
        # """
        # preVersion = self.gotVersion

        # # This call should populate the SSH version and carry on as usual.
        # transport.SSHClientTransport.dataReceived(self, data)

        # # We have now seen the SSH version in the banner.
        # # signal that the connection has been made successfully.
        # if self.gotVersion and not preVersion:
            # transport.SSHClientTransport.connectionMade(self)
