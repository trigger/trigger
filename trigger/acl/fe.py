#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fe - the File Editor. Uses RCS to maintain ACL policy versioning.
"""

__author__ = ('Jathan McCollum, Mark Ellzey Thomas, Michael Shields, '
              'Michael Harding')
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2002-2013, AOL Inc.'
__version__ = '1.2.1'

import os
import re
from simpleparse.error import ParserSyntaxError
import sys
import termios

import trigger.acl as acl
from trigger.acl.parser import TIP

psa_checks = (
    (lambda t: 'source-port' in t.match, 'source port'),
    (lambda t: 'tos' in t.match, 'ToS'),
    (lambda t: 'precedence' in t.match, 'precedence'),
    (lambda t: 'protocol' in t.match and 'igmp' in t.match['protocol'], 'IGMP')
)

def gsr_checks(a):
    '''PSA and SALSA checks, if the ACL is tagged appropriately.'''
    ok = True
    max_lines, psa = None, False
    if [c for c in a.comments if 'SALSA' in c]:
        max_lines = 128
    elif [c for c in a.comments if 'PSA-128' in c]:
        max_lines, psa = 128, True
    elif [c for c in a.comments if 'PSA-448' in c]:
        max_lines, psa = 448, True
    if max_lines and len(a.terms) > max_lines:
        print 'ACL has %d lines, max %d (GSR limit)' \
              % (len(a.terms), max_lines)
        ok = False
    if psa:
        for t in a.terms:
            for check, reason in psa_checks:
                if check(t):
                    print 'Match on %s not permitted in PSA mode' % reason
                    for line in t.output_ios():
                        print '    ' + line
                    ok = False
    return ok

def normalize(a):
    '''Fix up the ACL, and return False if there are problems.'''

    if isinstance(a, acl.PolicerGroup):
        return True

    ok = True

    # JunOS counter policy and duplicate term names.
    if a.format == 'junos':
        names = set()
        for t in a.terms:
            if t.name in names:
                print 'Duplicate term name', t.name
                ok = False
            else:
                names.add(t.name)

    # GSR checks.
    if a.format == 'ios':   # not ios_named
        if not gsr_checks(a):
            ok = False

    # Check for 10/8.
    for t in a.terms:
        for addr in ('address', 'source-address', 'destination-address'):
            for block in t.match.get(addr, []):
                if block == TIP('10.0.0.0/8'):
                    print 'Matching on 10.0.0.0/8 is never correct'
                    for line in t.output(a.format):
                        print '    ' + line
                    ok = False

    # Here is the place to put other policy checks; for example, we could
    # check blue to green HTTP and make sure all those terms have a comment
    # in a standardized format saying it was approved.

    return ok

def acltest(editfile):
    a = None
    try:
        a = acl.parse(file(editfile))
    except ParserSyntaxError, e:
        print e
    except TypeError, e:
        print  e
    except Exception, e:
        print 'ACL parse failed: ', sys.exc_type, ':', e
    if a and normalize(a):
        output = '\n'.join(a.output(replace=True)) + '\n'
        return True, output
    else:
        return False, None
