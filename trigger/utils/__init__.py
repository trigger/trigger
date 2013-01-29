# -*- coding: utf-8 -*-

"""
A collection of CLI tools and utilities used by Trigger.
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2008-2013, AOL Inc.'

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
