#!/usr/bin/env python

# tests/scripts.py

import os
import subprocess
import unittest
from pathlib import Path

ACLCONV = "aclconv"  # Now an entry point, not a script in bin/

os.environ["PYTHONPATH"] = str(Path.cwd())

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
        output, _errors = proc.communicate("access-list 100 deny ip any any")
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
