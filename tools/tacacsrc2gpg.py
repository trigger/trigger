#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
tacacsrc2gpg.py - Converts clear-text .tacacsrc to GPG-encrypted .tacacsrc.gpg

Intended for use when migrating from clear-text .tacacsrc to GPG.
"""

import os
import pwd
import socket
import sys

from trigger.tacacsrc import Tacacsrc, get_device_password, convert_tacacsrc
from trigger.utils.cli import yesno

prompt = 'This will overwrite your .tacacsrc.gpg and all gnupg configuration, are you sure?'
if not yesno(prompt):
    sys.exit(1)

(username, err, uid, gid, name, homedir, shell) = pwd.getpwuid(os.getuid())

print '''
======== [ READ ME READ ME READ ME READ ME ] ================
The following settings must be configured:

Real name: %s
Email Address: %s@%s
Comment: First Last
=============================================================
''' % (username, username, socket.getfqdn())

os.system('gpg --gen-key')

prompt2 = 'Would you like to convert your OLD tacacsrc configuration file to your new one?'
if yesno(prompt2) and os.path.isfile(os.path.join(homedir, '.tacacsrc')):
    convert_tacacsrc()
else:
    print "Old tacacsrc not converted."
    get_device_password()
