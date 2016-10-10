# -*- coding: utf-8 -*-

"""
Functions that perform network-based things like ping, port tests, etc.
"""

import os
import subprocess
import shlex
import socket
import telnetlib

from trigger.conf import settings


# Exports
__all__ = ('ping', 'test_tcp_port', 'test_ssh', 'address_is_internal')


# Constants
# SSH version strings used to validate SSH banners.
SSH_VERSION_STRINGS = (
    'SSH-1.99',
    'SSH-2.0',
    'dcos_sshd run in non-FIPS mode',  # Cisco Nexus not in FIPS mode
)


# Functions
def ping(host, count=1, timeout=5):
    """
    Returns pass/fail for a ping. Supports POSIX only.

    :param host:
        Hostname or address

    :param count:
        Repeat count

    :param timeout:
        Timeout in seconds

    >>> from trigger.utils import network
    >>> network.ping('aol.com')
    True
    >>> network.ping('192.168.199.253')
    False
    """

    ping_command = "ping -q -c%d -W%d %s" % (count, timeout, host)
    status = None
    with open(os.devnull, 'w') as devnull_fd:
        status = subprocess.call(
            shlex.split(ping_command),
            stdout=devnull_fd,
            stderr=devnull_fd,
            close_fds=True)

    # Linux RC: 0 = success, 256 = failure, 512 = unknown host
    # Darwin RC: 0 = success, 512 = failure, 17408 = unknown host
    return status == 0


def test_tcp_port(host, port=23, timeout=5, check_result=False,
                  expected_result=''):
    """
    Attempts to connect to a TCP port. Returns a Boolean.

    If ``check_result`` is set, the first line of output is retreived from the
    connection and the starting characters must match ``expected_result``.

    :param host:
        Hostname or address

    :param port:
        Destination port

    :param timeout:
        Timeout in seconds

    :param check_result:
        Whether or not to do a string check (e.g. version banner)

    :param expected_result:
        The expected result!

    >>> test_tcp_port('aol.com', 80)
    True
    >>> test_tcp_port('aol.com', 12345)
    False
    """
    try:
        t = telnetlib.Telnet(host, port, timeout)
        if check_result:
            result = t.read_some()
            t.close()
            return result.startswith(expected_result)
    except (socket.timeout, socket.error):
        return False

    t.close()
    return True


def test_ssh(host, port=22, timeout=5, version=SSH_VERSION_STRINGS):
    """
    Connect to a TCP port and confirm the SSH version. Defaults to SSHv2.

    Note that the default of ('SSH-1.99', 'SSH-2.0') both indicate SSHv2 per
    RFC 4253. (Ref: http://en.wikipedia.org/wiki/Secure_Shell#Version_1.99)

    :param host:
        Hostname or address

    :param port:
        Destination port

    :param timeout:
        Timeout in seconds

    :param version:
        The SSH version prefix (e.g. "SSH-2.0"). This may also be a tuple of
        prefixes.

    >>> test_ssh('localhost')
    True
    >>> test_ssh('localhost', version='SSH-1.5')
    False
    """
    return test_tcp_port(host, port, timeout, check_result=True,
                         expected_result=version)


def address_is_internal(ip):
    """
    Determines if an IP address is internal to your network. Relies on
    networks specified in :mod:`settings.INTERNAL_NETWORKS`.

    :param ip:
        IP address to test.

    >>> address_is_internal('1.1.1.1')
    False
    """
    for i in settings.INTERNAL_NETWORKS:
        if ip in i:
            return True
    return False
