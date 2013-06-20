===================================
Managing Credentials with .tacacsrc
===================================

About
=====

The `~trigger.tacacsrc` module provides an abstract interface to the management
and storage of user credentials in the ``.tacacsrc`` file. This is used
throughout Trigger to automatically retrieve credentials for a user whenever
they connect to devices.

How it works
============

The `~trigger.tacacsrc.Tacacsrc` class is the core interface for encrypting
credentials when they are stored, and decrypting the credentials when they are
retrieved. A unique ``.tacacsrc`` file is stored in each user's home directory,
and is forcefully set to be readable only (permissions: ``0400``) by the owning user.

There are two implementations, the first of which is the only one that is
officially supported at this time, and which is properly documented.

1. Shared key encryption

   This method is the default. It relies on a shared key to be stored in a file
   somewhere on the system. The location of this file can be customized in
   ``settings.py`` using :setting:`TACACSRC_KEYFILE`.

   This method has a glaring security flaw in that anyone who discerns the
   location of the keyfile can see the passphrase used for the encryption. This
   risk is mitigated somewhat by ensuring that each user's ``.tacacsrc`` has
   strict file permissions.

2. GPG encryption

   This method is experimental but is intended to be the long-term replacement
   for the shared key method. To enable GPG encryption, set
   :setting:`USE_GPG_AUTH` to ``True`` within ``settings.py``.

   This method is very secure because there is no centralized passphrase used
   for encryption. Each user chooses their own.

Usage
=====

Creating a .tacacsrc
--------------------

When you create an instance of `~trigger.tacacsrc.Tacacsrc`, it will try to
read the ``.tacacsrc`` file. If this file is not found, or cannot be properly
parsed, it will be initialized::

    >>> from trigger import tacacsrc
    >>> tcrc = tacacsrc.Tacacsrc()
    /home/jathan/.tacacsrc not found, generating a new one!

    Updating credentials for device/realm 'tacacsrc'
    Username: jathan
    Password:
    Password (again):

If you inspect the ``.tacacsrc`` file, you'll see that both the username and
password are encrypted::

    % cat ~/.tacacsrc
    # Saved by trigger.tacacsrc at 2012-06-23 11:38:51 PDT

    aol_uname_ = uiXq7eHEq2A=
    aol_pwd_ = GUpzkuFJfN8=

Retrieving stored credentials
-----------------------------

Credentials can be cached by realm. By default this realm is ``'aol'``, but you
can change that in ``settings.py`` using :setting:`DEFAULT_REALM`. Credentials
are stored as a dictionary under the ``.creds`` attribute, keyed by the realm
for each set of credentials::

    >>> tcrc.creds
    {'aol': Credentials(username='jathan', password='boguspassword', realm='aol')}

There is also a module-level function,
`~trigger.tacacsrc.get_device_password()`, that takes a realm name as an
argument, which will instantiate `~trigger.tacacsrc.Tacacsrc` for you and
returns the credentials for the realm::

    >>> tacacsrc.get_device_password('aol')
    Credentials(username='jathan', password='boguspassword', realm='aol')

Updating stored credentials
---------------------------

The module-level function `~trigger.tacacsrc.update_credentials()` will prompt
a user to update their stored credentials. It expects the realm key you would
like to update and an optional username you would like to use. If you don't
specify a user, the existing username for the realm is kept.

::

    >>> tacacsrc.update_credentials('aol')

    Updating credentials for device/realm 'aol'
    Username [jathan]:
    Password:
    Password (again):

    Credentials updated for user: 'jathan', device/realm: 'aol'.
    True
    >>> tcrc.creds
    {'aol': Credentials(username='jathan', password='panda', realm='aol')}

This function will return ``True`` upon a successful update to ``.tacacsrc``.

Using GPG encryption
====================

**EXPERIMENTAL! PROCEED AT YOUR OWN RISK!! FEEDBACK WELCOME!!**

Before you proceed, you must make sure to have gpg2 and gpg-agent installed on
your system.

Enabling GPG
------------

In ``settings.py`` set :setting:`USE_GPG_AUTH` to ``True``.

Generating your GPG key
-----------------------

Execute::

    gpg2 --gen-key

When asked fill these in with the values appropriate for you::

    Real name: jathan
    Email address: jathan.mccollum@teamaol.com
    Comment: Jathan McCollum

It will confirm::

    You selected this USER-ID:
        "jathan (Jathan McCollum) <jathan@marduk.itsec.aol.com>"

Here is a snippet to try and make this part of the core API, but is not yet
implemented::

    >>> import os, pwd, socket
    >>> pwd.getpwnam(os.getlogin()).pw_gecos
    'Jathan McCollum'
    >>> socket.gethostname()
    'wtfpwn.bogus.aol.com'
    >>> h = socket.gethostname()
    >>> u = os.getlogin()
    >>> n = pwd.getpwnam(u).pw_gecos
    >>> e = '%s@%s' % (u,h)
    >>> print '%s (%s) <%s>' % (u,n,e)
    jathan (Jathan McCollum) <jathan@wtfpwn.bogus.aol.com'

Convert your tacacsrc to GPG
----------------------------

Assuming you already have a "legacy" ``.tacacsrc`` file, execute::

    tacacsrc2gpg.py

It will want to generate your GPG key. This can take a VERY LONG time. We need a
workaround for this.

And then it outputs::

    This will overwrite your .tacacsrc.gpg and all gnupg configuration, are you sure? (y/N)
    Would you like to convert your OLD tacacsrc configuration file to your new one? (y/N)
    Converting old tacacsrc to new kind :)
    OLD
    /opt/bcs/packages/python-modules-2.0/lib/python/site-packages/simian/tacacsrc.py:125: DeprecationWarning: os.popen2 is deprecated.  Use the subprocess module.
      (fin,fout) = os.popen2('gpg2 --yes --quiet -r %s -e -o %s' % (self.username, self.file_name))

Update your gpg.conf
--------------------

Trigger should also do this for us, but alas...

Add ``'use-agent'`` to ``~/.gnupg/gpg.conf``::

    echo 'use-agent\n' > .gnupg/gpg.conf

This will allow you to unlock your GPG store at the beginning of the day, and
have the gpg-agent broker the communication encryption/decryption of the file
for 24 hours.

See if it works
---------------

1. Connect to a device.
2. It will prompt for passphrase
3. ...and connected! (aka Profit)

Other utilities
---------------

You may check if a user has a GPG-enabled credential store::

    >>> from trigger import tacacsrc
    >>> tcrc = tacacsrc.Tacacsrc()
    >>> tcrc.user_has_gpg()
    False

Convert ``.tacacsrc`` to ``.tacacsrc.gpg``::

    >>> tacacsrc.convert_tacacsrc()
