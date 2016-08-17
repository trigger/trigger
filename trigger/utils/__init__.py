# -*- coding: utf-8 -*-

"""
A collection of CLI tools and utilities used by Trigger.
"""

__author__ = 'Jathan McCollum, Mike Biancaniello'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2008-2013, AOL Inc.'

from collections import namedtuple
import re
from .cli import get_user

def crypt_md5(passwd):
    """
    Returns an md5-crypt hash of a clear-text password.

    To get md5-crypt from ``crypt(3)`` you must pass an 8-char string starting with
    '$1$' and ending with '$', resulting in a 12-char salt. This only works on
    systems where md5-crypt is default and is currently assumed to be Linux.

    :param passwd:
        Password string to be encrypted
    """
    import platform
    if platform.system() == 'Linux':
        import crypt
        import hashlib
        import time
        salt = '$1$' + hashlib.md5(str(time.time())).hexdigest()[0:8] + '$'
        crypted = crypt.crypt(passwd, salt)

    else:
        try:
            from passlib.hash import md5_crypt
        except ImportError:
            raise RuntimeError("""When not using Linux, generating md5-crypt password hashes requires the `passlib` module.""")
        else:
            crypted = md5_crypt.encrypt(passwd)

    return crypted

JuniperElement = namedtuple('JuniperElement', 'key value')
def strip_juniper_namespace(path, key, value):
    """
    Given a Juniper XML element, strip the namespace and return a 2-tuple.

    This is designed to be used as a ``postprocessor`` with
    `~trigger.utils.xmltodict.parse()`.

    :param key:
        The attribute name of the element.

    :param value:
        The value of the element.
    """
    marr = re.match(r"(ns1:|ns0:)", key)
    if marr:
        ns = marr.group(0)
        key = key.replace(ns, '')

    return JuniperElement(key, value)

NodePort = namedtuple('HostPort', 'nodeName nodePort')
def parse_node_port(nodeport, delimiter=':'):
    """
    Parse a string in format 'hostname' or 'hostname:port'  and return them
    as a 2-tuple.
    """
    node, _, port = nodeport.partition(delimiter)
    if port.isdigit():
        port = int(port)
    else:
        port = None

    return NodePort(str(node), port)
