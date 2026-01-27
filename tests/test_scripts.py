#!/usr/bin/env python

# tests/scripts.py

__author__ = "Michael Shields"
__maintainer__ = "Jathan McCollum"
__copyright__ = "Copyright 2005-2011 AOL Inc."
__version__ = "1.1"

import os
import subprocess
import unittest

ACLCONV = "aclconv"  # Now an entry point, not a script in bin/

os.environ["PYTHONPATH"] = os.getcwd()

# TODO (jathan): Add tests for all the scripts!!


class Aclconv(unittest.TestCase):
    # This should be expanded.
    def testI2J(self):
        """Convert IOS to JunOS."""
        # Python 3: Use subprocess.Popen instead of os.popen2
        proc = subprocess.Popen(
            [ACLCONV, "-j", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        output, errors = proc.communicate("access-list 100 deny ip any any")
        self.assertEqual(proc.returncode, 0)
        correct_output = """\
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
"""
        self.assertEqual(output, correct_output)


if __name__ == "__main__":
    unittest.main()
