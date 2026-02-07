"""Abstract interface to .tacacsrc credentials file.

Designed to interoperate with the legacy DeviceV2 implementation, but
provide a reasonable API on top of that.  The name and format of the
.tacacsrc file are not ideal, but compatibility matters.
"""

__author__ = "Jathan McCollum, Mark Thomas, Michael Shields"
__maintainer__ = "Jathan McCollum"
__email__ = "jmccollum@salesforce.com"
__copyright__ = "Copyright 2006-2012, AOL Inc.; 2013 Salesforce.com"

import getpass
import os
import pwd
import sys
from base64 import decodebytes as decodestring
from base64 import encodebytes as encodestring
from collections import namedtuple
from pathlib import Path
from time import localtime, strftime

from cryptography.hazmat.backends.openssl import backend as openssl_backend
from cryptography.hazmat.primitives import ciphers

# Python 3: distutils deprecated, use packaging instead
from packaging.version import Version
from twisted.python import log

from trigger.conf import settings

# Python 3 / cryptography 48+: TripleDES moved to decrepit module
try:
    from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
except ImportError:
    from cryptography.hazmat.primitives.ciphers.algorithms import TripleDES

# Exports
__all__ = (
    "Credentials",
    "Tacacsrc",
    "convert_tacacsrc",
    "get_device_password",
    "prompt_credentials",
    "update_credentials",
    "validate_credentials",
)

# Credential object stored in Tacacsrc.creds
Credentials = namedtuple("Credentials", "username password realm")


# Exceptions
class TacacsrcError(Exception):
    pass


class CouldNotParse(TacacsrcError):
    pass


class MissingPassword(TacacsrcError):
    pass


class MissingRealmName(TacacsrcError):
    pass


class VersionMismatch(TacacsrcError):
    pass


# Functions
def get_device_password(device=None, tcrc=None):
    """Fetch the password for a device/realm or create a new entry for it.
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
        print(f"\nCredentials not found for device/realm {device!r}, prompting...")
        creds = prompt_credentials(device)
        tcrc.creds[device] = creds
        tcrc.write()

    return creds


def prompt_credentials(device, user=None):
    """Prompt for username, password and return them as Credentials namedtuple.

    :param device: Device or realm name to store
    :param user: (Optional) If set, use as default username
    """
    if not device:
        msg = "You must specify a device/realm name."
        raise MissingRealmName(msg)

    creds = ()
    # Make sure we can even get tty i/o!
    if sys.stdin.isatty() and sys.stdout.isatty():
        print(f"\nUpdating credentials for device/realm {device!r}")

        user_default = ""
        if user:
            user_default = f" [{user}]"

        username = input(f"Username{user_default}: ") or user
        if username == "":
            print("\nYou must specify a username, try again!")
            return prompt_credentials(device, user=user)

        passwd = getpass.getpass("Password: ")
        passwd2 = getpass.getpass("Password (again): ")
        if not passwd:
            print("\nPassword cannot be blank, try again!")
            return prompt_credentials(device, user=username)

        if passwd != passwd2:
            print("\nPasswords did not match, try again!")
            return prompt_credentials(device, user=username)

        creds = Credentials(username, passwd, device)

    return creds


def update_credentials(device, username=None):
    """Update the credentials for a given device/realm. Assumes the same username
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
    """Given a set of credentials, try to return a `~trigger.tacacsrc.Credentials`
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
    if (not creds) or isinstance(creds, str) or (len(creds) not in (2, 3)):
        log.msg("Creds not valid, fetching from .tacacsrc...")
        tcrc = Tacacsrc()
        return tcrc.creds.get(realm, get_device_password(realm, tcrc))

    # If it's a dict, get the values
    if hasattr(creds, "values"):
        log.msg("Creds is a dict, converting to values...")
        creds = creds.values()

    # If it's missing realm, add it.
    if len(creds) == 2:
        log.msg("Creds is a 2-tuple, making into namedtuple...")
        username, password = creds
        return Credentials(username, password, realm)

    # Or just make it go...
    if len(creds) == 3:
        log.msg("Creds is a 3-tuple, making into namedtuple...")
        return Credentials(*creds)

    msg = "THIS SHOULD NOT HAVE HAPPENED!!"
    raise RuntimeError(msg)


def convert_tacacsrc():
    """Converts old .tacacsrc to new .tacacsrc.gpg."""
    print("Converting old tacacsrc to new kind :)")
    tco = Tacacsrc(old=True)
    tcn = Tacacsrc(old=False, gen=True)
    tcn.creds = tco.creds
    tcn.write()


def _perl_unhex_old(c):
    """Emulate Crypt::TripleDES's bizarre handling of keys, which relies on
    the fact that you can pass Perl's pack('H*') a string that contains
    anything, not just hex digits.  "The result for bytes "g".."z" and
    "G".."Z" is not well-defined", says perlfunc(1).  Smash!

    This function can be safely removed once GPG is fully supported.
    """
    if "a" <= c <= "z":
        return (ord(c) - ord("a") + 10) & 0xF
    if "A" <= c <= "Z":
        return (ord(c) - ord("A") + 10) & 0xF
    return ord(c) & 0xF


def _perl_pack_Hstar_old(s):
    """Used with _perl_unhex_old(). Ghetto hack.

    This function can be safely removed once GPG is fully supported.
    """
    r = ""
    while len(s) > 1:
        r += chr((_perl_unhex_old(s[0]) << 4) | _perl_unhex_old(s[1]))
        s = s[2:]
    if len(s) == 1:
        r += _perl_unhex_old(s[0])
    return r


# Classes
class Tacacsrc:
    """Encrypts, decrypts and returns credentials for use by network devices and
    other tools.

    Pass use_gpg=True to force GPG, otherwise it relies on
    settings.USE_GPG_AUTH

    `*_old` functions should be removed after everyone is moved to the new
    system.
    """

    def __init__(
        self,
        tacacsrc_file=None,
        use_gpg=settings.USE_GPG_AUTH,
        generate_new=False,
    ):
        """Open .tacacsrc (tacacsrc_file or $TACACSRC or ~/.tacacsrc), or create
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
        self.version = Version("2.0")

        # If we're not generating a new file and gpg is enabled, turn it off if
        # the right files can't be found.
        if not self.generate_new and self.use_gpg and not self.user_has_gpg():
            log.msg(".tacacsrc.gpg not setup, disabling GPG", debug=True)
            self.use_gpg = False

        log.msg(f"Using GPG method: {self.use_gpg!r}", debug=True)
        log.msg(f"Got username: {self.username!r}", debug=True)

        # Set the .tacacsrc file location
        if self.file_name is None:
            self.file_name = settings.TACACSRC

            # GPG uses '.tacacsrc.gpg'
            if self.use_gpg:
                self.file_name += ".gpg"

        # Check if the file exists
        if not Path(self.file_name).exists():
            print(f"{self.file_name} not found, generating a new one!")
            self.generate_new = True

        if self.use_gpg:
            if not self.generate_new:
                self.rawdata = self._decrypt_and_read()
                self.creds = self._parse()
            else:
                self.creds[settings.DEFAULT_REALM] = prompt_credentials(
                    device="tacacsrc",
                )
                self.write()
        else:
            # If passphrase is enable, use that
            if settings.TACACSRC_USE_PASSPHRASE:
                passphrase = settings.TACACSRC_PASSPHRASE
                import hashlib

                # Python 3 requires encoding string to bytes before hashing
                if isinstance(passphrase, str):
                    passphrase = passphrase.encode("utf-8")
                key = hashlib.md5(passphrase).hexdigest()[:24]  # noqa: S324 - MD5 used for legacy key derivation, not security
                self.key = key
            # Otherwise read from keyfile.
            else:
                self.key = self._get_key_old(settings.TACACSRC_KEYFILE)

            if not self.generate_new:
                self.rawdata = self._read_file_old()
                self.creds = self._parse_old()
                if self.creds_updated:  # _parse_old() might set this flag
                    log.msg("creds updated, writing to file", debug=True)
                    self.write()
            else:
                self.creds[settings.DEFAULT_REALM] = prompt_credentials(
                    device="tacacsrc",
                )
                self.write()

    def _get_key_nonce_old(self):
        """Yes, the key nonce is the userid.  Awesome, right?"""
        return pwd.getpwuid(os.getuid())[0] + "\n"

    def _get_key_old(self, keyfile):
        """Of course, encrypting something in the filesystem using a key
        in the filesystem really doesn't buy much.  This is best referred
        to as obfuscation of the .tacacsrc.
        """
        try:
            with Path(keyfile).open() as kf:
                key = kf.readline().strip()
        except OSError as err:
            msg = f"Keyfile at {keyfile} not found. Please create it."
            raise CouldNotParse(msg) from err

        if not key:
            msg = f"Keyfile at {keyfile} must contain a passphrase."
            raise CouldNotParse(msg)

        key += self._get_key_nonce_old()
        key = _perl_pack_Hstar_old((key + (" " * 48))[:48])
        assert len(key) == 24

        return key

    def _parse_old(self):
        """Parses .tacacsrc and returns dictionary of credentials."""
        data = {}
        creds = {}

        # Cleanup the rawdata
        for idx, line in enumerate(self.rawdata):
            line = line.strip()  # noqa: PLW2901 - eat \n
            lineno = idx + 1  # increment index for actual lineno

            # Skip blank lines and comments
            if any((line.startswith("#"), line == "")):
                log.msg(f"skipping {line!r}", debug=True)
                continue

            if line.count(" = ") > 1:
                msg = f"Malformed line {line!r} at line {lineno}"
                raise CouldNotParse(msg)

            key, _sep, val = line.partition(" = ")
            if val == "":
                continue  # Don't add a key with a missing value
                msg = f"Missing value for key {key!r} at line {lineno}"
                raise CouldNotParse(msg)

            # Check for version
            if key == "version":
                if val != self.version:
                    msg = f"Bad .tacacsrc version ({val})"
                    raise VersionMismatch(msg)
                continue

            # Make sure tokens can be parsed
            realm, token, end = key.split("_")
            if end != "" or (realm, token) in data:
                msg = f"Could not parse {line!r} at line {lineno}"
                raise CouldNotParse(msg)

            data[(realm, token)] = self._decrypt_old(val)
            del key, val, line

        # Store the creds, if a password is empty, try to prompt for it.
        for (realm, key), val in data.items():
            if key == "uname":
                try:
                    creds[realm] = Credentials(val, data[(realm, "pwd")], realm)
                except KeyError:
                    print(f"\nMissing password for {realm!r}, initializing...")
                    self.update_creds(creds=creds, realm=realm, user=val)
            elif key == "pwd":
                pass
            else:
                msg = f"Unknown .tacacsrc entry ({realm}_{val})"
                raise CouldNotParse(msg)

        self.data = data
        return creds

    def update_creds(self, creds, realm, user=None):
        """Update username/password for a realm/device and set self.creds_updated
        bit to trigger .write().

        :param creds: Dictionary of credentials keyed by realm
        :param realm: The realm to update within the creds dict
        :param user: (Optional) Username passed to prompt_credentials()
        """
        creds[realm] = prompt_credentials(realm, user)
        log.msg("setting self.creds_updated flag", debug=True)
        self.creds_updated = True
        new_user = creds[realm].username
        print(f"\nCredentials updated for user: {new_user!r}, device/realm: {realm!r}.")

    def _encrypt_old(self, s):
        """Encodes using the old method. Adds a newline for you."""
        # Ensure key and plaintext are bytes for cryptography library
        key = self.key if isinstance(self.key, bytes) else self.key.encode("latin-1")
        plaintext = s if isinstance(s, bytes) else s.encode("latin-1")

        des = TripleDES(key)
        cipher = ciphers.Cipher(des, ciphers.modes.ECB(), backend=openssl_backend)  # noqa: S305 - legacy credential handling requires ECB mode
        encryptor = cipher.encryptor()

        # Crypt::TripleDES pads with *spaces*!  How 1960. Pad it so the
        # length is a multiple of 8.
        padding_len = (8 - len(plaintext) % 8) % 8
        padding = b" " * padding_len

        cipher_text = encryptor.update(plaintext + padding) + encryptor.finalize()

        # We need to return a newline if a field is empty so as not to break
        # .tacacsrc parsing (trust me, this is easier)
        return (
            encodestring(cipher_text).decode("ascii").replace("\n", "") or ""
        ) + "\n"

    def _decrypt_old(self, s):
        """Decodes using the old method. Strips newline for you."""
        # Ensure key is bytes for cryptography library
        key = self.key if isinstance(self.key, bytes) else self.key.encode("latin-1")
        des = TripleDES(key)
        cipher = ciphers.Cipher(des, ciphers.modes.ECB(), backend=openssl_backend)  # noqa: S305 - legacy credential handling requires ECB mode
        decryptor = cipher.decryptor()
        # Ensure s is bytes for base64.decodebytes
        s_bytes = s if isinstance(s, bytes) else s.encode("ascii")
        # rstrip() to undo space-padding; unfortunately this means that
        # passwords cannot end in spaces.
        plaintext = decryptor.update(decodestring(s_bytes)) + decryptor.finalize()
        return plaintext.rstrip(b" ").decode("latin-1")

    def _read_file_old(self):
        """Read old style file and return the raw data."""
        self._update_perms()
        with Path(self.file_name).open() as f:
            return f.readlines()

    def _write_old(self):
        """Write old style to disk. Newlines provided by _encrypt_old(), so don't fret!"""
        out = [
            "# Saved by {} at {}\n\n".format(
                self.__module__,
                strftime("%Y-%m-%d %H:%M:%S %Z", localtime()),
            ),
        ]

        for realm, (uname, password, _) in self.creds.items():
            out.append(f"{realm}_uname_ = {self._encrypt_old(uname)}")
            out.append(f"{realm}_pwd_ = {self._encrypt_old(password)}")

        with Path(self.file_name).open("w+") as fd:
            fd.writelines(out)

        self._update_perms()

    def _decrypt_and_read(self):
        """Decrypt file using GPG and return the raw data."""
        ret = []
        for x in os.popen(f"gpg2 --no-tty --quiet -d {self.file_name}"):  # noqa: S605
            x = x.rstrip()  # noqa: PLW2901
            ret.append(x)

        return ret

    def _encrypt_and_write(self):
        """Encrypt using GPG and dump password data to disk."""
        fin, _fout = os.popen2(  # noqa: S605
            f"gpg2 --yes --quiet -r {self.username} -e -o {self.file_name}",
        )
        for line in self.rawdata:
            print(line, file=fin)

    def _write_new(self):
        """Replace self.rawdata with current password details."""
        out = [
            "# Saved by {} at {}\n\n".format(
                self.__module__,
                strftime("%Y-%m-%d %H:%M:%S %Z", localtime()),
            ),
        ]

        for realm, (uname, password, _) in self.creds.items():
            out.append(f"{realm}_uname_ = {uname}")
            out.append(f"{realm}_pwd_ = {password}")

        self.rawdata = out
        self._encrypt_and_write()
        self._update_perms()

    def write(self):
        """Writes .tacacsrc(.gpg) using the accurate method (old vs. new)."""
        if self.use_gpg:
            return self._write_new()

        return self._write_old()

    def _update_perms(self):
        """Enforce -rw------- on the creds file."""
        Path(self.file_name).chmod(0o600)

    def _parse(self):
        """Parses .tacacsrc.gpg and returns dictionary of credentials."""
        data = {}
        creds = {}
        for line in self.rawdata:
            if line.find("#") != -1:
                line = line[: line.find("#")]  # noqa: PLW2901
            line = line.strip()  # noqa: PLW2901
            if len(line):
                k, v = line.split(" = ")
                if k == "version":
                    if v != self.version:
                        msg = f"Bad .tacacsrc version ({v})"
                        raise VersionMismatch(msg)
                else:
                    realm, s, _junk = k.split("_")
                    assert (realm, s) not in data
                    data[(realm, s)] = v

        for (realm, k), v in data.items():
            if k == "uname":
                creds[realm] = Credentials(v, data[(realm, "pwd")], realm)
            elif k == "pwd":
                pass
            else:
                msg = f"Unknown .tacacsrc entry ({realm}_{v})"
                raise CouldNotParse(msg)

        return creds

    def user_has_gpg(self):
        """Checks if user has .gnupg directory and .tacacsrc.gpg file."""
        gpg_dir = Path(self.user_home) / ".gnupg"
        tacacsrc_gpg = Path(self.user_home) / ".tacacsrc.gpg"

        # If not generating new .tacacsrc.gpg, we want both to be True
        return bool(gpg_dir.is_dir() and tacacsrc_gpg.is_file())
