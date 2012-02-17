# -*- coding: utf-8 -*-

"""Abstract interface to .tacacsrc credentials file.

Designed to interoperate with the legacy DeviceV2 implementation, but
provide a reasonable API on top of that.  The name and format of the
.tacacsrc file are not ideal, but compatibility matters.
"""

__author__ = 'Jathan McCollum, Mark Thomas, Michael Shields'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2006-2011, AOL Inc.'

from base64 import decodestring, encodestring
from collections import namedtuple
from Crypto.Cipher import DES3
from distutils.version import LooseVersion
from time import strftime, localtime
import os
import pwd
import sys
from trigger.conf import settings

# Defaults
DEBUG = False

# Exports
__all__ = ('get_device_password', 'prompt_credentials', 'convert_tacacsrc', 'Tacacsrc')

# Credential object stored in Tacacsrc.creds
Credentials = namedtuple('Credentials', 'username password')

# Exceptions
class Error(Exception): pass
class TacacsrcError(Error): pass
class TacacsrcParseError(TacacsrcError): pass
class TacacsrcVersionError(TacacsrcError): pass


# Functions
def get_device_password(device=None):
    """
    Fetch the password for a device/realm or create a new entry for it.
    If device is not passed, 'aol' is used, which is default realm for most devices.
    """
    tcrc = Tacacsrc()

    # If device isn't passed, assume we are initializing the .tacacsrc.
    try:
        creds = tcrc.creds[device]
        print 'Fetching credentials from %s' % tcrc.file_name
    except KeyError:
        print 'Credentials not found for %s, prompting...' % device
        creds = prompt_credentials(device)
        tcrc.creds[device] = creds
        tcrc.write()

    return creds

def prompt_credentials(device, user=None):
    """Prompt for username, password and return them as 2-tuple."""
    if not device:
        raise TacacsrcError('You must specify a device/realm name.')

    creds = ()
    # Make sure we can even get tty i/o!
    if sys.stdin.isatty() and sys.stdout.isatty():
        import getpass
        username = user or getpass._raw_input('\nUsername for %s: ' % device)
        passwd = getpass.getpass('Password for %s: ' % device)
        passwd2 = getpass.getpass('Retype password: ')
        if passwd != passwd2:
            print 'Passwords did not match, try again!'
            return prompt_credentials(device, user=username)

        #creds = (username, passwd)
        creds = Credentials(username, passwd)

    return creds

def convert_tacacsrc():
    """Converts old .tacacsrc to new .tacacsrc.gpg."""
    print "Converting old tacacsrc to new kind :)"
    tco = Tacacsrc(old=True)
    tcn = Tacacsrc(old=False, gen=True)
    tcn.creds = tco.creds
    tcn.write()

def _perl_unhex_old(c):
    """
    Emulate Crypt::TripleDES's bizarre handling of keys, which relies on
    the fact that you can pass Perl's pack('H*') a string that contains
    anything, not just hex digits.  "The result for bytes "g".."z" and
    "G".."Z" is not well-defined", says perlfunc(1).  Smash!

    This function can be safely removed once GPG is fully supported.
    """
    if 'a' <= c <= 'z':
        return (ord(c) - ord('a') + 10) & 0xf
    if 'A' <= c <= 'Z':
        return (ord(c) - ord('A') + 10) & 0xf
    return ord(c) & 0xf

def _perl_pack_Hstar_old(s):
    """
    Used with _perl_unhex_old(). Ghetto hack.

    This function can be safely removed once GPG is fully supported.
    """
    r = ''
    while len(s) > 1:
        r += chr((_perl_unhex_old(s[0]) << 4) | _perl_unhex_old(s[1]))
        s = s[2:]
    if len(s) == 1:
        r += _perl_unhex_old(s[0])
    return r


# Classes
class Tacacsrc(object):
    """
    Encrypts, decrypts and returns credentials for use by network devices and
    other tools.

    Pass use_gpg=True to force GPG, otherwise it relies on
    settings.USE_GPG_AUTH

    `*_old` functions should be removed after everyone is moved to the new
    system.
    """
    def __init__(self, tacacsrc_file=None, use_gpg=settings.USE_GPG_AUTH, generate_new=False):
        """
        Open .tacacsrc (tacacsrc_file or $TACACSRC or ~/.tacacsrc), or create
        a new file if one cannot be found on disk.

        If settings.USE_GPG_AUTH is enabled, tries to use GPG (.tacacsrc.gpg).
        """
        self.file_name = tacacsrc_file
        self.use_gpg = use_gpg
        self.generate_new = generate_new
        self.userinfo = pwd.getpwuid(os.getuid())
        self.username = self.userinfo.pw_name
        self.user_home = self.userinfo.pw_dir
        self.data = []
        self.creds = {}
        self.version = LooseVersion('2.0')

        # If we're not generating a new file and gpg is enabled, turn it off if
        # the right files can't be found.
        if not self.generate_new:
            if self.use_gpg and not self.user_has_gpg():
                if DEBUG: print ".tacacsrc.gpg not setup, disabling GPG"
                self.use_gpg = False

        if DEBUG:
            print "Using GPG method:", self.use_gpg
            print "Got username:" , self.username

        # Set the .tacacsrc file location
        if self.file_name is None:
            self.file_name = os.getenv('TACACSRC', os.path.join(self.user_home, '.tacacsrc'))

            # GPG uses '.tacacsrc.gpg'
            if self.use_gpg:
                self.file_name += '.gpg'

        # Check if the file exists
        if not os.path.exists(self.file_name):
            print '%s not found, generating a new one!' % self.file_name
            self.generate_new = True

        if self.use_gpg:
            if not self.generate_new:
                self.rawdata = self._decrypt_and_read()
                self.creds = self._parse()
            else:
                self.creds['aol'] = prompt_credentials(device='tacacsrc')
                self.write()
        else:
            self.key = self._get_key_old(os.getenv('TACACSRC_KEYFILE', settings.TACACSRC_KEYFILE))

            if not self.generate_new:
                self.rawdata = self._read_file_old()
                self.creds = self._parse_old()
            else:
                self.creds['aol'] = prompt_credentials(device='tacacsrc')
                self.write()

    def _get_key_nonce_old(self):
        """Yes, the key nonce is the userid.  Awesome, right?"""
        return pwd.getpwuid(os.getuid())[0] + '\n'

    def _get_key_old(self, keyfile):
        '''Of course, encrypting something in the filesystem using a key
        in the filesystem really doesn't buy much.  This is best referred
        to as obfuscation of the .tacacsrc.'''
        key = open(keyfile).readline()
        if key[-1].isspace():
            key = key[:-1]
        key += self._get_key_nonce_old()
        key = _perl_pack_Hstar_old((key + (' ' * 48))[:48])
        assert(len(key) == 24)

        return key

    def _parse_old(self):
        """
        Parses .tacacsrc and returns dictionary of credentials.
        """
        data = {}
        creds = {}
        for line in self.rawdata:
            if line.find('#') != -1:
                line = line[:line.find('#')]

            line = line.strip()

            if line:
                k, v = line.split(' = ')
                if k == 'version':
                    if v != self.version:
                        raise TacacsrcVersionError('Bad .tacacsrc version (%s)' % v)
                else:
                    realm, s, junk = k.split('_')
                    if junk != '' or (realm, s) in data:
                        raise TacacsrcParseError("Could not parse: %s" % line)
                    #assert(junk == '')
                    #assert((realm, s) not in data)
                    data[(realm, s)] = self._decrypt_old(v)

        for (realm, k), v in data.iteritems():
            if k == 'uname':
                #creds[realm] = (v, data[(realm, 'pwd')])
                creds[realm] = Credentials(v, data[(realm, 'pwd')])
            elif k == 'pwd':
                pass
            else:
                raise TacacsrcParseError('Unknown .tacacsrc entry (%s_%s)' % (realm, v))

        return creds

    def _encrypt_old(self, s):
        """Encodes using the old method. Adds a newline for you."""
        cryptobj = DES3.new(self.key, DES3.MODE_ECB)
        # Crypt::TripleDES pads with *spaces*!  How 1960.
        padding = len(s) % 8 and ' ' * (8 - len(s)%8) or ''

        return encodestring(cryptobj.encrypt(s + padding))

    def _decrypt_old(self, s):
        """Decodes using the old method. Strips newline for you."""
        cryptobj = DES3.new(self.key, DES3.MODE_ECB)
        # rstrip() to undo space-padding; unfortunately this means that
        # passwords cannot end in spaces.

        return cryptobj.decrypt(decodestring(s)).rstrip(' ')

    def _read_file_old(self):
        """Read old style file and return the raw data."""
        return open(self.file_name, 'r').readlines()

    def _write_old(self):
        """Write old style to disk. Newlines provided by _encrypt_old(), so don't fret!"""
        out = ['# Saved by %s at %s\n\n' % \
            (self.__module__, strftime('%Y-%m-%d %H:%M:%S %Z', localtime()))]
        for realm, (uname, pwd) in self.creds.iteritems():
            out.append('%s_uname_ = %s' % (realm, self._encrypt_old(uname)))
            out.append('%s_pwd_ = %s' % (realm, self._encrypt_old(pwd)))

        fd = open(self.file_name, 'w+')
        fd.writelines(out)

    def _decrypt_and_read(self):
        """Decrypt file using GPG and return the raw data."""
        ret = []
        for x in os.popen('gpg2 --no-tty --quiet -d %s' % self.file_name):
            x = x.rstrip()
            ret.append(x)

        return ret

    def _encrypt_and_write(self):
        """Encrypt using GPG and dump password data to disk."""
        (fin,fout) = os.popen2('gpg2 --yes --quiet -r %s -e -o %s' % (self.username, self.file_name))
        for line in self.rawdata:
            print >>fin, line

    def _write_new(self):
        """Replace self.rawdata with current password details."""
        out = ['# Saved by %s at %s\n\n' % \
            (self.__module__, strftime('%Y-%m-%d %H:%M:%S %Z', localtime()))]

        for realm, (uname, pwd) in self.creds.iteritems():
            out.append('%s_uname_ = %s' % (realm, uname))
            out.append('%s_pwd_ = %s' % (realm, pwd))

        self.rawdata = out
        self._encrypt_and_write()

    def write(self):
        """Writes .tacacsrc(.gpg) using the accurate method (old vs. new)."""
        if self.use_gpg:
            return self._write_new()

        return self._write_old()

    def _parse(self):
        """Parses .tacacsrc.gpg and returns dictionary of credentials."""
        data = {}
        creds = {}
        for line in self.rawdata:
            if line.find('#') != -1:
                line = line[:line.find('#')]
            line = line.strip()
            if len(line):
                k, v = line.split(' = ')
                if k == 'version':
                    if v != self.version:
                        raise TacacsrcVersionError('Bad .tacacsrc version (%s)' % v)
                else:
                    realm, s, junk = k.split('_')
                    #assert(junk == '')
                    assert((realm, s) not in data)
                    data[(realm, s)] = v#self._decrypt(v)

        for (realm, k), v in data.iteritems():
            if k == 'uname':
                #creds[realm] = (v, data[(realm, 'pwd')])
                creds[realm] = Credentials(v, data[(realm, 'pwd')])
            elif k == 'pwd':
                pass
            else:
                raise TacacsrcParseError('Unknown .tacacsrc entry (%s_%s)' % (realm, v))

        return creds

    def user_has_gpg(self):
        """Checks if user has .gnupg directory and .tacacsrc.gpg file."""
        gpg_dir = os.path.join(self.user_home, '.gnupg')
        tacacsrc_gpg = os.path.join(self.user_home, '.tacacsrc.gpg')

        # If not generating new .tacacsrc.gpg, we want both to be True
        if os.path.isdir(gpg_dir) and os.path.isfile(tacacsrc_gpg):
            return True

        return False
