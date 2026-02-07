#!/usr/bin/env python

"""gen_tacacsrc.py - Simple, stupid tool that creates a .tacacsrc if is not found.
"""

from trigger.tacacsrc import *

t = Tacacsrc()
if hasattr(t, "rawdata"):
    print("You already have %s, bye!" % t.file_name)
else:
    print("\nWrote %s!" % t.file_name)
