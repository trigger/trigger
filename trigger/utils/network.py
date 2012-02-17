# -*- coding: utf-8 -*-

"""
Functions that perform network-based things like ping, port tests, etc.
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2009-2011, AOL Inc.'

import commands
import socket
import telnetlib
from trigger.conf import settings


# Exports
__all__ = ('ping', 'test_tcp_port', 'address_is_internal',)


# Functions
def ping(host, count=1, timeout=5):
    """
    Returns pass/fail for a ping. Supports POSIX only.

    :param host: Hostname or address
    :param count: Repeat count
    :param timeout: Timeout in seconds

    >>> from trigger.utils import network
    >>> network.ping('aol.com')
    True
    >>> network.ping('192.168.199.253')
    False
    """
    ping_command = "ping -q -c%d -W%d %s" % (count, timeout, host)
    status, results = commands.getstatusoutput(ping_command)

    # Linux RC: 0 = success, 256 = failure, 512 = unknown host
    # Darwin RC: 0 = success, 512 = failure, 17408 = unknown host
    if status != 0:
        return False
    return True

def test_tcp_port(host, port=23, timeout=5):
    """
    Attempts to connect to a TCP port. Returns a boolean.

    :param host: Hostname or address
    :param port: Destination port
    :param timeout: Timeout in seconds

    >>> network.test_tcp_port('aol.com', 80)
    True
    >>> network.test_tcp_port('aol.com', 12345)
    False
    """
    try:
        t = telnetlib.Telnet(host, port, timeout)
        t.close()
    except (socket.timeout, socket.error):
        return False

    return True

def address_is_internal(ip):
    """
    Determines if an IP address is internal to your network. Relies on 
    networks specified in :mod:`settings.INTERNAL_NETWORKS`.

    :param ip: IP address to test. 

    >>> network.address_is_internal('1.1.1.1')
    False
    """
    for i in settings.INTERNAL_NETWORKS:
        if ip in i:
            return True
    return False
