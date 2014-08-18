# -*- coding: utf-8 -*-

"""
Parse and manipulate network access control lists.

This library doesn't completely follow the border of the valid/invalid ACL
set, which is determined by multiple vendors and not completely documented
by any of them.  We could asymptotically approach that with an enormous
amount of testing, although it would require a 'flavor' flag (vendor,
router model, software version) for full support.  The realistic goal
is to catch all the errors that we see in practice, and to accept all
the ACLs that we use in practice, rather than to try to reject *every*
invalid ACL and accept *every* valid ACL.

>>> from trigger.acl import parse
>>> aclobj = parse("access-list 123 permit tcp any host 10.20.30.40 eq 80")
>>> aclobj.terms
[<Term: None>]
"""

"""
7/15/2014
This file was split into smaller modules: dicts, grammar, junos, ios, and support.
These modules are then included back into parser.py.
This makes the code more readable. 
"""

__author__ = 'Jathan McCollum, Mike Biancaniello, Michael Harding, Michael Shields'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathanism@aol.com'
__copyright__ = 'Copyright 2006-2013, AOL Inc.; 2013 Saleforce.com'

import IPy
from simpleparse import objectgenerator
from simpleparse.common import comments, strings
from simpleparse.dispatchprocessor import (DispatchProcessor, dispatch,
                                           dispatchList)
from simpleparse.parser import Parser
import socket
from trigger import exceptions
from trigger.conf import settings
  
from support import *
from junos import *
from ios import *

# Exports
__all__ = (
    # Constants,
    'ports',
    # Functions
    'check_range',
    'default_processor',
    'do_port_lookup',
    'do_protocol_lookup',
    'literals',
    'make_nondefault_processor',
    'parse',
    'strip_comments',
    'S',
    # Classes
    'ACL',
    'ACLParser',
    'ACLProcessor',
    'Comment',
    'Matches',
    'Policer',
    'PolicerGroup',
    'Protocol',
    'RangeList',
    'Remark',
    'Term',
    'TermList',
    'TIP',
)

# Temporary resting place for comments, so the rest of the parser can
# ignore them.  Yes, this makes the library not thread-safe.
Comments = []

#
# Parsing infrastructure
#

class ACLProcessor(DispatchProcessor):
    pass

def default_processor(self, (tag, start, stop, subtags), buffer):
    if not subtags:
        return buffer[start:stop]
    elif len(subtags) == 1:
        return dispatch(self, subtags[0], buffer)
    else:
        return dispatchList(self, subtags, buffer)

def make_nondefault_processor(action):
    if callable(action):
        def processor(self, (tag, start, stop, subtags), buffer):
            if tag in subtagged:
                results = [getattr(self, subtag[0])(subtag, buffer)
                           for subtag in subtags]
                return action(strip_comments(results))
            else:
                return action(buffer[start:stop])
    else:
        def processor(self, (tag, start, stop, subtags), buffer):
            return action

    return processor

grammar = []
for production, rule in rules.iteritems():
    if isinstance(rule, tuple):
        assert len(rule) == 2
        setattr(ACLProcessor, production, make_nondefault_processor(rule[1]))
        grammar.append('%s := %s' % (production, rule[0]))
    else:
        setattr(ACLProcessor, production, default_processor)
        grammar.append('%s := %s' % (production, rule))

grammar = '\n'.join(grammar)

class ACLParser(Parser):
    def buildProcessor(self):
        return ACLProcessor()

###parser = ACLParser(grammar)

def parse(input_data):
    """
    Parse a complete ACL and return an ACL object. This should be the only
    external interface to the parser.

    >>> from trigger.acl import parse
    >>> aclobj = parse("access-list 123 permit tcp any host 10.20.30.40 eq 80")
    >>> aclobj.terms
    [<Term: None>]

    :param input_data:
        An ACL policy as a string or file-like object.
    """
    parser = ACLParser(grammar)

    try:
        data = input_data.read()
    except AttributeError:
        data = input_data

    ## parse the acl
    success, children, nextchar = parser.parse(data)

    if success and nextchar == len(data):
        assert len(children) == 1
        return children[0]
    else:
        line = data[:nextchar].count('\n') + 1
        column = len(data[data[nextchar].rfind('\n'):nextchar]) + 1
        raise exceptions.ParseError('Could not match syntax.  Please report as a bug.', line, column)
