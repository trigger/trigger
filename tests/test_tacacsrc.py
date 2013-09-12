#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Jathan McCollum, Michael Shields'
__maintainer__ = 'Jathan McCollum'
__copyright__ = 'Copyright 2005-2011 AOL Inc.; 2013 Salesforce.com'
__version__ = '2.0'


from StringIO import StringIO
import os
import unittest
import tempfile
from trigger.tacacsrc import Tacacsrc, Credentials


# Constants
RIGHT_CREDS = Credentials('jschmoe', 'abc123', 'aol')
RIGHT_TACACSRC = {
    'aol_uname_': 'jschmoe',
    'aol_pwd_': 'abc123',
}
TACACSRC = os.getenv('TACACSRC')


def miniparser(data, tcrc):
    """Manually parse .tacacsrc lines into a dict"""
    lines = [line.strip() for line in data]
    lines = [line for line in lines if line and not line.startswith('#')]
    ret = {}
    for line in lines:
        k, _, v = line.partition(' = ')
        ret[k] = tcrc._decrypt_old(v)
    return ret

class Testing_Tacacsrc(Tacacsrc):
    def _get_keyfile_nonce(self):
        '''Dependency injection'''
        return 'shields'

class TacacsrcTest(unittest.TestCase):
    def testRead(self):
        """Test reading .tacacsrc."""
        t = Testing_Tacacsrc()
        self.assertEqual(t.version, '2.0')
        self.assertEqual(t.creds['aol'], RIGHT_CREDS)

    def testWrite(self):
        """Test writing .tacacsrc."""
        _, file_name = tempfile.mkstemp('_tacacsrc')
        t = Testing_Tacacsrc(generate_new=False)
        t.creds['aol'] = RIGHT_CREDS
        # Overload the default file_name w/ our temp file
        t.file_name = file_name
        t.write()

        # Read the file we wrote back in and check it against what we think it
        # should look like.
        output = miniparser(t._read_file_old(), t)
        self.assertEqual(output, RIGHT_TACACSRC)

        # And then compare it against the manually parsed value using
        # miniparser()
        with open(TACACSRC, 'r') as fd:
            lines = fd.readlines()
            self.assertEqual(output, miniparser(lines, t))
        os.remove(file_name)

if __name__ == "__main__":
    unittest.main()
