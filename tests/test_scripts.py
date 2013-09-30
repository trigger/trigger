#!/usr/bin/env python
# -*- coding: utf-8 -*-

# tests/scripts.py

__author__ = 'Michael Shields'
__maintainer__ = 'Jathan McCollum'
__copyright__ = 'Copyright 2005-2011 AOL Inc.'
__version__ = '1.1'

import os
import unittest

ACLCONV = 'bin/aclconv'

os.environ['PYTHONPATH'] = os.getcwd()

# TODO (jathan): Add tests for all the scripts!!

class Aclconv(unittest.TestCase):
    # This should be expanded.
    def testI2J(self):
        """Convert IOS to JunOS."""
        child_in, child_out = os.popen2(ACLCONV + ' -j -')
        child_in.write('access-list 100 deny ip any any')
        self.assertEqual(child_in.close(), None)
        correct_output = '''\
firewall {
replace:
    filter 100j {
        term T1 {
            then {
                reject;
                count T1;
            }
        }
    }
}
'''
        self.assertEqual(child_out.read(), correct_output)
        self.assertEqual(child_out.close(), None)

if __name__ == "__main__":
    unittest.main()
