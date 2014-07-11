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

class ACL(object):
    """
    An abstract access-list object intended to be created by the :func:`parse`
    function.
    """
    def __init__(self, name=None, terms=None, format=None, family=None,
                 interface_specific=False):
        check_name(name, exceptions.ACLNameError, max_len=24)
        self.name = name
        self.family = family
        self.interface_specific = interface_specific
        self.format = format
        self.policers = []
        if terms:
            self.terms = terms
        else:
            self.terms = TermList()
        global Comments
        self.comments = Comments
        Comments = []

    def __repr__(self):
        return '<ACL: %s>' % self.name

    def __str__(self):
        return '\n'.join(self.output(format=self.format, family=self.family))

    def output(self, format=None, *largs, **kwargs):
        """
        Output the ACL data in the specified format.
        """
        if format is None:
            format = self.format
        return getattr(self, 'output_' + format)(*largs, **kwargs)

    def output_junos(self, replace=False, family=None):
        """
        Output the ACL in JunOS format.

        :param replace: If set the ACL is wrapped in a
            ``firewall { replace: ... }`` section.
        :param family: If set, the value is used to wrap the ACL in a
            ``family inet { ...}`` section.
        """
        if self.name == None:
            raise exceptions.MissingACLName('JunOS format requires a name')

        # Make sure we properly set 'family' so it's automatically used for
        # printing.
        if family is not None:
            assert family in ('inet', 'inet6')
        else:
            family = self.family

        # Prep the filter body
        out = ['filter %s {' % self.name]
        out += ['    ' + c.output_junos() for c in self.comments if c]

        # Add the policers
        if self.policers:
            for policer in self.policers:
                out += ['    ' + x for x in policer.output()]

        # Add interface-specific
        if self.interface_specific:
            out += ['    ' + 'interface-specific;']

        # Add the terms
        for t in self.terms:
            out += ['    ' + x for x in t.output_junos()]
        out += ['}']

        # Wrap in 'firewall {}' thingy.
        if replace:
            '''
            #out = ['firewall {', 'replace:'] + ['    '+x for x in out] + ['}']
            if family is None: # This happens more often
                out = ['firewall {', 'replace:'] + ['    '+x for x in out] + ['}']
            else:
                out = ['firewall {', family_head, 'replace:'] + ['    '+x for x in out] + [family_tail, '}']
            '''

            head = ['firewall {']
            body = ['replace:'] + ['    ' + x for x in out]
            tail = ['}']
            if family is not None:
                body = ['family %s {' % family] + body + tail
                body = ['    ' + x for x in body]
            out = head + body + tail

        return out

    def output_ios(self, replace=False):
        """
        Output the ACL in IOS traditional format.

        :param replace: If set the ACL is preceded by a ``no access-list`` line.
        """
        if self.name == None:
            raise exceptions.MissingACLName('IOS format requires a name')
        try:
            x = int(self.name)
            if not (100 <= x <= 199 or 2000 <= x <= 2699):
                raise exceptions.BadACLName('IOS ACLs are 100-199 or 2000-2699')
        except (TypeError, ValueError):
            raise exceptions.BadACLName('IOS format requires a number as name')
        out = [c.output_ios() for c in self.comments]
        if self.policers:
            raise exceptions.VendorSupportLacking('policers not supported in IOS')
        if replace:
            out.append('no access-list ' + self.name)
        prefix = 'access-list %s ' % self.name
        for t in self.terms:
            out += [x for x in t.output_ios(prefix)]
        return out

    def output_ios_brocade(self, replace=False, receive_acl=False):
        """
        Output the ACL in Brocade-flavored IOS format.

        The difference between this and "traditional" IOS are:

            - Stripping of comments
            - Appending of ``ip rebind-acl`` or ``ip rebind-receive-acl`` line

        :param replace: If set the ACL is preceded by a ``no access-list`` line.
        :param receive_acl: If set the ACL is suffixed with a ``ip
            rebind-receive-acl' instead of ``ip rebind-acl``.
        """
        self.strip_comments()

        # Check if the is_receive_acl attr was set by the parser. This way we
        # don't always have to pass the argument.
        if hasattr(self, 'is_receive_acl') and not receive_acl:
            receive_acl = self.is_receive_acl

        out = self.output_ios(replace=replace)
        if receive_acl:
            out.append('ip rebind-receive-acl %s' % self.name)
        else:
            out.append('ip rebind-acl %s' % self.name)

        return out

    def output_ios_named(self, replace=False):
        """
        Output the ACL in IOS named format.

        :param replace: If set the ACL is preceded by a ``no access-list`` line.
        """
        if self.name == None:
            raise exceptions.MissingACLName('IOS format requires a name')
        out = [c.output_ios_named() for c in self.comments]
        if self.policers:
            raise exceptions.VendorSupportLacking('policers not supported in IOS')
        if replace:
            out.append('no ip access-list extended ' + self.name)
        out.append('ip access-list extended %s' % self.name)
        for t in self.terms:
            out += [x for x in t.output_ios_named(' ')]
        return out

    def output_iosxr(self, replace=False):
        """
        Output the ACL in IOS XR format.

        :param replace: If set the ACL is preceded by a ``no ipv4 access-list`` line.
        """
        if self.name == None:
            raise exceptions.MissingACLName('IOS XR format requires a name')
        out = [c.output_iosxr() for c in self.comments]
        if self.policers:
            raise exceptions.VendorSupportLacking('policers not supported in IOS')
        if replace:
            out.append('no ipv4 access-list ' + self.name)
        out.append('ipv4 access-list ' + self.name)
        counter = 0        # 10 PRINT "CISCO SUCKS"  20 GOTO 10
        for t in self.terms:
            if t.name == None:
                for line in t.output_ios():
                    counter = counter + 10
                    out += [' %d %s' % (counter, line)]
            else:
                try:
                    counter = int(t.name)
                    if not 1 <= counter <= 2147483646:
                        raise exceptions.BadTermName('Term %d out of range' % counter)
                    line = t.output_iosxr()
                    if len(line) > 1:
                        raise exceptions.VendorSupportLacking('one name per line')
                    out += [' ' + line[0]]
                except ValueError:
                    raise exceptions.BadTermName('IOS XR requires numbered terms')
        return out

    def name_terms(self):
        """Assign names to all unnamed terms."""
        n = 1
        for t in self.terms:
            if t.name is None:
                t.name = 'T%d' % n
                n += 1

    def strip_comments(self):
        """Strips all comments from ACL header and all terms."""
        self.comments = []
        for term in self.terms:
            term.comments = []

#
# Parsing infrastructure
#

class ACLProcessor(DispatchProcessor):
    pass

def strip_comments(tags):
    if tags is None:
        return
    noncomments = []
    for tag in tags:
        if isinstance(tag, Comment):
            Comments.append(tag)
        else:
            noncomments.append(tag)
    return noncomments

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
