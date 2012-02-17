#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
gen_tacacsrc.py - Simple, stupid tool that creates a .tacacsrc if is not found.
"""

__author__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2006-2011, AOL Inc.'
__version__ = '1.9'

from trigger.tacacsrc import *

t = Tacacsrc()
if hasattr(t, 'rawdata'):
    print 'You already have %s, bye!' % t.file_name
else:
    print '\nWrote %s!' % t.file_name
