#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Michael Shields <shieldszero@aol.com>'
__maintainer__ = 'Jathan McCollum'
__copyright__ = 'Copyright 2005-2011 AOL Inc.'
__version__ = '1.5'


from StringIO import StringIO
import os
import unittest

from trigger.tacacsrc import Tacacsrc

RIGHT_CREDS = ('jschmoe', 'abc123')
RIGHT_TACACSRC = {
    'version': '2.0',
    'aol_uname_': 'jschmoe',
    'aol_pwd_': 'abc123',
}


def miniparser(s):
    lines = [line.strip() for line in s.split('\n')]
    lines = [line for line in lines if not line.startswith('#')]
    return dict([line.split(' = ') for line in lines if len(line)])


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
        buf = StringIO()
        t = Testing_Tacacsrc(False)
        t.creds['aol'] = RIGHT_CREDS
        t.file = buf
        t.write()
        output = miniparser(buf.getvalue())
        self.assertEqual(output, RIGHT_TACACSRC)
        self.assertEqual(output, miniparser(file(os.getenv('TACACSRC')).read()))


if __name__ == "__main__":
    unittest.main()
