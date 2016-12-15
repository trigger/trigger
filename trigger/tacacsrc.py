# -*- coding: utf-8 -*-

"""Abstract interface to .tacacsrc credentials file.

Designed to interoperate with the legacy DeviceV2 implementation, but
provide a reasonable API on top of that.  The name and format of the
.tacacsrc file are not ideal, but compatibility matters.
"""

__author__ = 'Jathan McCollum, Mark Thomas, Michael Shields'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jmccollum@salesforce.com'
__copyright__ = 'Copyright 2006-2012, AOL Inc.; 2013 Salesforce.com'

from base64 import decodestring, encodestring
from collections import namedtuple
from distutils.version import LooseVersion
import getpass
from time import strftime, localtime
import os
import pwd
import sys
from twisted.python import log
from trigger.conf import settings

from cryptography.hazmat.backends.openssl import backend as openssl_backend
from cryptography.hazmat.primitives import ciphers

# Exports
__all__ = ('get_device_password', 'prompt_credentials', 'convert_tacacsrc',
           'update_credentials', 'validate_credentials', 'Credentials', 'Tacacsrc')

# Credential object stored in Tacacsrc.creds
Credentials = namedtuple('Credentials', 'username password realm')

# Exceptions
class TacacsrcError(Exception): pass
class CouldNotParse(TacacsrcError): pass
class MissingPassword(TacacsrcError): pass
class MissingRealmName(TacacsrcError): pass
class VersionMismatch(TacacsrcError): pass


# Functions
def get_device_password(device=None, tcrc=None):
    """
    Fetch the password for a device/realm or create a new entry for it.
    If device is not passed, ``settings.DEFAULT_REALM`` is used, which is default
    realm for most devices.

    :param device:
        Realm or device name to updated

    :param device:
        Optional `~trigger.tacacsrc.Tacacsrc` instance
    """
    if tcrc is None:
        tcrc = Tacacsrc()

    # If device isn't passed, assume we are initializing the .tacacsrc.
    try:
        creds = tcrc.creds[device]
    except KeyError:
        print '\nCredentials not found for device/realm %r, prompting...' % device
        creds = prompt_credentials(device)
        tcrc.creds[device] = creds
        tcrc.write()

    return creds

def prompt_credentials(device, user=None):
    """
    Prompt for username, password and return them as Credentials namedtuple.

    :param device: Device or realm name to store
    :param user: (Optional) If set, use as default username
    """
    if not device:
        raise MissingRealmName('You must specify a device/realm name.')

    creds = ()
    # Make sure we can even get tty i/o!
    if sys.stdin.isatty() and sys.stdout.isatty():
        print '\nUpdating credentials for device/realm %r' % device

        user_default = ''
        if user:
            user_default = ' [%s]' % user

        username = getpass._raw_input('Username%s: ' % user_default) or user
        if username == '':
            print '\nYou must specify a username, try again!'
            return prompt_credentials(device, user=user)

        passwd = getpass.getpass('Password: ')
        passwd2 = getpass.getpass('Password (again): ')
        if not passwd:
            print '\nPassword cannot be blank, try again!'
            return prompt_credentials(device, user=username)

        if passwd != passwd2:
            print '\nPasswords did not match, try again!'
            return prompt_credentials(device, user=username)

        creds = Credentials(username, passwd, device)

    return creds

def update_credentials(device, username=None):
    """
    Update the credentials for a given device/realm. Assumes the same username
    that is already cached unless it is passed.

    This may seem redundant at first compared to Tacacsrc.update_creds() but we
    need this factored out so that we don't end up with a race condition when
    credentials are messed up.

    Returns True if it actually updated something or None if it didn't.

    :param device: Device or realm name to update
    :param username: Username for credentials
    """
    tcrc = Tacacsrc()
    if tcrc.creds_updated:
        return None

    mycreds = tcrc.creds.get(device, tcrc.creds[settings.DEFAULT_REALM])
    if username is None:
        username = mycreds.username

    tcrc.update_creds(tcrc.creds, mycreds.realm, username)
    tcrc.write()

    return True

def validate_credentials(creds=None):
    """
    Given a set of credentials, try to return a `~trigger.tacacsrc.Credentials`
    object.

    If ``creds`` is unset it will fetch from ``.tacacsrc``.

    Expects either a 2-tuple of (username, password) or a 3-tuple of (username,
    password, realm). If only (username, password) are provided, realm will be populated from
    :setting:`DEFAULT_REALM`.

    :param creds:
        A tuple of credentials.

    """
    realm = settings.DEFAULT_REALM

    # If it isn't set or it's a string, or less than 1 or more than 3 items,
    # get from .tacacsrc
    if (not creds) or (type(creds) == str) or (len(creds) not in (2, 3)):
        log.msg('Creds not valid, fetching from .tacacsrc...')
        tcrc = Tacacsrc()
        return tcrc.creds.get(realm, get_device_password(realm, tcrc))

    # If it's a dict, get the values
    if hasattr(creds, 'values'):
        log.msg('Creds is a dict, converting to values...')
        creds = creds.values()

    # If it's missing realm, add it.
    if len(creds) == 2:
        log.msg('Creds is a 2-tuple, making into namedtuple...')
        username, password = creds
        return Credentials(username, password, realm)

    # Or just make it go...
    elif len(creds) == 3:
        log.msg('Creds is a 3-tuple, making into namedtuple...')
        return Credentials(*creds)

    raise RuntimeError('THIS SHOULD NOT HAVE HAPPENED!!')

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
    def __init__(self, tacacsrc_file=None, use_gpg=settings.USE_GPG_AUTH,
                 generate_new=False):
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
        self.creds_updated = False
        self.version = LooseVersion('2.0')

        # If we're not generating a new file and gpg is enabled, turn it off if
        # the right files can't be found.
        if not self.generate_new:
            if self.use_gpg and not self.user_has_gpg():
                log.msg(".tacacsrc.gpg not setup, disabling GPG", debug=True)
                self.use_gpg = False

        log.msg("Using GPG method: %r" % self.use_gpg, debug=True)
        log.msg("Got username: %r" % self.username, debug=True)

        # Set the .tacacsrc file location
        if self.file_name is None:
            self.file_name = settings.TACACSRC

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
                self.creds[settings.DEFAULT_REALM] = prompt_credentials(device='tacacsrc')
                self.write()
        else:
            # If passphrase is enable, use that
            if settings.TACACSRC_USE_PASSPHRASE:
                passphrase = settings.TACACSRC_PASSPHRASE
                import hashlib
                key = hashlib.md5(passphrase).hexdigest()[:24] # 24 bytes
                self.key = key
            # Otherwise read from keyfile.
            else:
                self.key = self._get_key_old(settings.TACACSRC_KEYFILE)

            if not self.generate_new:
                self.rawdata = self._read_file_old()
                self.creds = self._parse_old()
                if self.creds_updated: # _parse_old() might set this flag
                    log.msg('creds updated, writing to file', debug=True)
                    self.write()
            else:
                self.creds[settings.DEFAULT_REALM] = prompt_credentials(device='tacacsrc')
                self.write()

    def _get_key_nonce_old(self):
        """Yes, the key nonce is the userid.  Awesome, right?"""
        return pwd.getpwuid(os.getuid())[0] + '\n'

    def _get_key_old(self, keyfile):
        '''Of course, encrypting something in the filesystem using a key
        in the filesystem really doesn't buy much.  This is best referred
        to as obfuscation of the .tacacsrc.'''
        try:
            with open(keyfile, 'r') as kf:
                key = kf.readline().strip()
        except IOError as err:
            msg = 'Keyfile at %s not found. Please create it.' % keyfile
            raise CouldNotParse(msg)

        if not key:
            msg = 'Keyfile at %s must contain a passphrase.' % keyfile
            raise CouldNotParse(msg)

        key += self._get_key_nonce_old()
        key = _perl_pack_Hstar_old((key + (' ' * 48))[:48])
        assert(len(key) == 24)

        return key

    def _parse_old(self):
        """Parses .tacacsrc and returns dictionary of credentials."""
        data = {}
        creds = {}

        # Cleanup the rawdata
        for idx, line in enumerate(self.rawdata):
            line = line.strip() # eat \n
            lineno = idx + 1 # increment index for actual lineno

            # Skip blank lines and comments
            if any((line.startswith('#'), line == '')):
                log.msg('skipping %r' % line, debug=True)
                continue
            #log.msg('parsing %r' % line, debug=True)

            if line.count(' = ') > 1:
                raise CouldNotParse("Malformed line %r at line %s" % (line, lineno))

            key, sep, val = line.partition(' = ')
            if val == '':
                continue # Don't add a key with a missing value
                raise CouldNotParse("Missing value for key %r at line %s" % (key, lineno))

            # Check for version
            if key == 'version':
                if val != self.version:
                    raise VersionMismatch('Bad .tacacsrc version (%s)' % v)
                continue

            # Make sure tokens can be parsed
            realm, token, end = key.split('_')
            if end != '' or (realm, token) in data:
                raise CouldNotParse("Could not parse %r at line %s" % (line, lineno))

            data[(realm, token)] = self._decrypt_old(val)
            del key, val, line

        # Store the creds, if a password is empty, try to prompt for it.
        for (realm, key), val in data.iteritems():
            if key == 'uname':
                try:
                    #creds[realm] = Credentials(val, data[(realm, 'pwd')])
                    creds[realm] = Credentials(val, data[(realm, 'pwd')], realm)
                except KeyError:
                    print '\nMissing password for %r, initializing...' % realm
                    self.update_creds(creds=creds, realm=realm, user=val)
                    #raise MissingPassword('Missing password for %r' % realm)
            elif key == 'pwd':
                pass
            else:
                raise CouldNotParse('Unknown .tacacsrc entry (%s_%s)' % (realm, val))

        self.data = data
        return creds

    def update_creds(self, creds, realm, user=None):
        """
        Update username/password for a realm/device and set self.creds_updated
        bit to trigger .write().

        :param creds: Dictionary of credentials keyed by realm
        :param realm: The realm to update within the creds dict
        :param user: (Optional) Username passed to prompt_credentials()
        """
        creds[realm] = prompt_credentials(realm, user)
        log.msg('setting self.creds_updated flag', debug=True)
        self.creds_updated = True
        new_user = creds[realm].username
        print '\nCredentials updated for user: %r, device/realm: %r.' % \
              (new_user, realm)

    def _encrypt_old(self, s):
        """Encodes using the old method. Adds a newline for you."""
        des = ciphers.algorithms.TripleDES(self.key)
        cipher = ciphers.Cipher(des, ciphers.modes.ECB(), backend=openssl_backend)
        encryptor = cipher.encryptor()

        # Crypt::TripleDES pads with *spaces*!  How 1960. Pad it so the
        # length is a multiple of 8.
        padding = len(s) % 8 and ' ' * (8 - len(s) % 8) or ''

        cipher_text = encryptor.update(s + padding) + encryptor.finalize()

        # We need to return a newline if a field is empty so as not to break
        # .tacacsrc parsing (trust me, this is easier)
        return (encodestring(cipher_text).replace('\n', '') or '' ) + '\n'

    def _decrypt_old(self, s):
        """Decodes using the old method. Strips newline for you."""
        des = ciphers.algorithms.TripleDES(self.key)
        cipher = ciphers.Cipher(des, ciphers.modes.ECB(), backend=openssl_backend)
        decryptor = cipher.decryptor()
        # rstrip() to undo space-padding; unfortunately this means that
        # passwords cannot end in spaces.
        return decryptor.update(decodestring(s)).rstrip(' ') + decryptor.finalize()

    def _read_file_old(self):
        """Read old style file and return the raw data."""
        self._update_perms()
        with open(self.file_name, 'r') as f:
            return f.readlines()

    def _write_old(self):
        """Write old style to disk. Newlines provided by _encrypt_old(), so don't fret!"""
        out = ['# Saved by %s at %s\n\n' % \
            (self.__module__, strftime('%Y-%m-%d %H:%M:%S %Z', localtime()))]

        for realm, (uname, pwd, _) in self.creds.iteritems():
            #log.msg('encrypting %r' % ((uname, pwd),), debug=True)
            out.append('%s_uname_ = %s' % (realm, self._encrypt_old(uname)))
            out.append('%s_pwd_ = %s' % (realm, self._encrypt_old(pwd)))

        with open(self.file_name, 'w+') as fd:
            fd.writelines(out)

        self._update_perms()

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

        for realm, (uname, pwd, _) in self.creds.iteritems():
            out.append('%s_uname_ = %s' % (realm, uname))
            out.append('%s_pwd_ = %s' % (realm, pwd))

        self.rawdata = out
        self._encrypt_and_write()
        self._update_perms()

    def write(self):
        """Writes .tacacsrc(.gpg) using the accurate method (old vs. new)."""
        if self.use_gpg:
            return self._write_new()

        return self._write_old()

    def _update_perms(self):
        """Enforce -rw------- on the creds file"""
        os.chmod(self.file_name, 0600)

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
                        raise VersionMismatch('Bad .tacacsrc version (%s)' % v)
                else:
                    realm, s, junk = k.split('_')
                    #assert(junk == '')
                    assert((realm, s) not in data)
                    data[(realm, s)] = v#self._decrypt(v)

        for (realm, k), v in data.iteritems():
            if k == 'uname':
                #creds[realm] = (v, data[(realm, 'pwd')])
                #creds[realm] = Credentials(v, data[(realm, 'pwd')])
                creds[realm] = Credentials(v, data[(realm, 'pwd')], realm)
            elif k == 'pwd':
                pass
            else:
                raise CouldNotParse('Unknown .tacacsrc entry (%s_%s)' % (realm, v))

        return creds

    def user_has_gpg(self):
        """Checks if user has .gnupg directory and .tacacsrc.gpg file."""
        gpg_dir = os.path.join(self.user_home, '.gnupg')
        tacacsrc_gpg = os.path.join(self.user_home, '.tacacsrc.gpg')

        # If not generating new .tacacsrc.gpg, we want both to be True
        if os.path.isdir(gpg_dir) and os.path.isfile(tacacsrc_gpg):
            return True

        return False
