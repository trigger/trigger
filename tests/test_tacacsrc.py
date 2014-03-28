#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Jathan McCollum, Michael Shields'
__maintainer__ = 'Jathan McCollum'
__copyright__ = 'Copyright 2005-2011 AOL Inc.; 2013 Salesforce.com'
__version__ = '2.0.1'


from StringIO import StringIO
import os
import unittest
import tempfile
from mock import patch
from trigger.conf import settings
from trigger.tacacsrc import Tacacsrc, Credentials


# Constants
aol = Credentials('jschmoe', 'abc123', 'aol')
AOL_TACACSRC = {
    'aol_uname_': 'jschmoe',
    'aol_pwd_': 'abc123',
}
RIGHT_PERMS = '0600'

MEDIUMPWCREDS = Credentials('MEDIUMPWCREDS', 'MEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUM', 'MEDIUMPWCREDS')
MEDIUMPW_TACACSRC = {
  'MEDIUMPWCREDS_uname_': 'MEDIUMPWCREDS',
  'MEDIUMPWCREDS_pwd_': 'MEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUM',
} 

LONGPWCREDS = Credentials('LONGPWCREDS', 'LONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONG', 'LONGPWCREDS')
LONGPW_TACACSRC = {
   'LONGPWCREDS_uname_': 'LONGPWCREDS',
   'LONGPWCREDS_pwd_': 'LONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONG',
}

EMPTYPWCREDS = Credentials('EMPTYPWCREDS', '', 'EMPTYPWCREDS')
EMPTYPW_TACACSRC = {
   'EMPTYPWCREDS_uname_': 'EMPTYPWCREDS',
   'EMPTYPWCREDS_pwd_': '',
}

LIST_OF_CREDS = ['aol', 'MEDIUMPWCREDS', 'LONGPWCREDS', ]  
LIST_OF_TACACSRC = [ AOL_TACACSRC, MEDIUMPW_TACACSRC, LONGPW_TACACSRC ]  
ALL_CREDS = [ (name,eval(name)) for name in LIST_OF_CREDS] 
ALL_TACACSRC = dict() 
[ALL_TACACSRC.update(x) for x in LIST_OF_TACACSRC]

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
    def _get_key_nonce_old(self):
        '''Dependency injection'''
        return 'jschmoe\n'

class TacacsrcTest(unittest.TestCase):
    def testRead(self):
        """Test reading .tacacsrc."""
        t = Testing_Tacacsrc()
        for name,value in ALL_CREDS:
          self.assertEqual(t.version, '2.0')
          self.assertEqual(t.creds['%s' % name], value)

    def _get_perms(self, filename):
        """Get octal permissions for a filename"""
        # We only want the lower 4 bits (negative index)
        return oct(os.stat(filename).st_mode)[-4:]

    def testWrite(self):
        """Test writing .tacacsrc."""
        _, file_name = tempfile.mkstemp('_tacacsrc')
        t = Testing_Tacacsrc(generate_new=False)

        for name,value in ALL_CREDS:
          t.creds['%s' % name] = value
        # Overload the default file_name w/ our temp file or
        # create a new tacacsrc by setting file_name to 'tests/data/tacacsrc'
          t.file_name = file_name 
          t.write()

        # Read the file we wrote back in and check it against what we think it
        # should look like.
        self.maxDiff = None 
        output = miniparser(t._read_file_old(), t)
        self.assertEqual(output, ALL_TACACSRC) 

        # And then compare it against the manually parsed value using
        # miniparser()
        with open(settings.TACACSRC, 'r') as fd:
            lines = fd.readlines()
            self.assertEqual(output, miniparser(lines, t))
        os.remove(file_name)

    def test_brokenpw(self):
        self.assertRaises(ValueError, Testing_Tacacsrc, tacacsrc_file='tests/data/brokenpw_tacacsrc') 

    def test_emptypw(self):
        devnull = open(os.devnull, 'w')
        with patch('trigger.tacacsrc.prompt_credentials', side_effect=KeyError): 
          with patch('sys.stdout', devnull):
            self.assertRaises(KeyError, Testing_Tacacsrc, tacacsrc_file='tests/data/emptypw_tacacsrc') 

    def test_perms(self):
        """Test that permissions are being enforced."""
        t = Testing_Tacacsrc()
        fname = t.file_name
        # First make sure perms are set
        old_perms = self._get_perms(fname)
        self.assertEqual(old_perms, RIGHT_PERMS)
        os.chmod(fname, 0666) # Make it world-writable
        new_perms = self._get_perms(fname)
        self.assertNotEqual(new_perms, RIGHT_PERMS)

if __name__ == "__main__":
    unittest.main()
