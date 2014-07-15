# -*- coding: utf-8 -*-

"""
This code is originally from parser.py. It consists of a lot of classes which
support the various modules for parsing. This file is not meant to by used by itself.

# Functions
    'check_name',
    'check_range',
    'do_dscp_lookup',
    'do_icmp_type_lookup',
    'do_icmp_code_lookup',
    'do_ip_option_lookup',
    'do_lookup',
    'do_port_lookup',
    'do_protocol_lookup',
    'make_inverse_mask',
    'strip_comments',
# Classes
    'ACL',
    'Comment',
    'Matches',
    'Modifiers',
    'MyDict',
    'Protocol',
    'RangeList',
    'Term',
    'TermList',
    'TIP',
"""

#Copied metadata from parser.py
__author__ = 'Jathan McCollum, Mike Biancaniello, Michael Harding, Michael Shields'
__editor__ = 'Joseph Malone'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathanism@aol.com'
__copyright__ = 'Copyright 2006-2013, AOL Inc.; 2013 Saleforce.com'

import IPy
from trigger import exceptions
from trigger.conf import settings
from dicts import *

# Temporary resting place for comments, so the rest of the parser can
# ignore them.  Yes, this makes the library not thread-safe.
Comments = []

def check_name(name, exc, max_len=255, extra_chars=' -_.'):
    """
    Test whether something is a valid identifier (for any vendor).
    This means letters, numbers, and other characters specified in the
    @extra_chars argument.  If the string is invalid, throw the specified
    exception.

    :param name: The name to test.
    :param exc: Exception type to raise if the name is invalid.
    :param max_len: Integer of the maximum length of the name.
    :param extra_chars: Extra non-alphanumeric characters to allow in the name.
    """
    if name is None:
        return
    if name == '':
        raise exc('Name cannot be null string')
    if len(name) > max_len:
        raise exc('Name "%s" cannot be longer than %d characters' % (name, max_len))
    for char in name:
        if not ((extra_chars is not None and char in extra_chars)
                or (char >= 'a' and char <= 'z')
                or (char >= 'A' and char <= 'Z')
                or (char >= '0' and char <= '9')):
            raise exc('Invalid character "%s" in name "%s"' % (char, name))

def check_range(values, min, max):
    for value in values:
        try:
            for subvalue in value:
                check_range([subvalue], min, max)
        except TypeError:
            if not min <= value <= max:
                raise exceptions.BadMatchArgRange('match arg %s must be between %d and %d'
                                                  % (str(value), min, max))

# Having this take the dictionary itself instead of a function is very slow.
def do_lookup(lookup_func, arg):
    if isinstance(arg, tuple):
        return tuple([do_lookup(lookup_func, elt) for elt in arg])

    try:
        return int(arg)
    except TypeError:
        return arg
    except ValueError:
        pass
    # Ok, look it up by name.
    try:
        return lookup_func(arg)
    except KeyError:
        raise exceptions.UnknownMatchArg('match argument "%s" not known' % arg)

def do_protocol_lookup(arg):
    if isinstance(arg, tuple):
        return (Protocol(arg[0]), Protocol(arg[1]))
    else:
        return Protocol(arg)

def do_port_lookup(arg):
    return do_lookup(lambda x: ports[x], arg)

def do_icmp_type_lookup(arg):
    return do_lookup(lambda x: icmp_types[x], arg)

def do_icmp_code_lookup(arg):
    return do_lookup(lambda x: icmp_codes[x], arg)

def do_ip_option_lookup(arg):
    return do_lookup(lambda x: ip_option_names[x], arg)

def do_dscp_lookup(arg):
    return do_lookup(lambda x: dscp_names[x], arg)

def make_inverse_mask(prefixlen):
    """
    Return an IP object of the inverse mask of the CIDR prefix.

    :param prefixlen:
        CIDR prefix
    """
    inverse_bits = 2 ** (32 - prefixlen) - 1
    return TIP(inverse_bits)

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

class MyDict(dict):
    """
    A dictionary subclass to collect common behavior changes used in container
    classes for the ACL components: Modifiers, Matches.
    """
    def __init__(self, d=None, **kwargs):
        if d:
            if not hasattr(d, 'keys'):
                d = dict(d)
            self.update(d)
        if kwargs:
            self.update(kwargs)

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, str(self))

    def __str__(self):
        return ', '.join(['%s %s' % (k, v) for k, v in self.iteritems()])

    def update(self, d):
        '''Force this to go through __setitem__.'''
        for k, v in d.iteritems():
            self[k] = v

class Modifiers(MyDict):
    """
    Container class for modifiers. These are only supported by JunOS format
    and are ignored by all others.
    """
    def __setitem__(self, key, value):
        # Handle argument-less modifiers first.
        if key in ('log', 'sample', 'syslog', 'port-mirror'):
            if value not in (None, True):
                raise exceptions.ActionError('"%s" action takes no argument' % key)
            super(Modifiers, self).__setitem__(key, None)
            return
        # Everything below requires an argument.
        if value is None:
            raise exceptions.ActionError('"%s" action requires an argument' %
                                         key)
        if key == 'count':
            # JunOS 7.3 docs say this cannot contain underscores and that
            # it must be 24 characters or less, but this appears to be false.
            # Doc bug filed 2006-02-09, doc-sw/68420.
            check_name(value, exceptions.BadCounterName, max_len=255)
        elif key == 'forwarding-class':
            check_name(value, exceptions.BadForwardingClassName)
        elif key == 'ipsec-sa':
            check_name(value, exceptions.BadIPSecSAName)
        elif key == 'loss-priority':
            if value not in ('low', 'high'):
                raise exceptions.ActionError('"loss-priority" must be "low" or "high"')
        elif key == 'policer':
            check_name(value, exceptions.BadPolicerName)
        else:
            raise exceptions.ActionError('invalid action: ' + str(key))
        super(Modifiers, self).__setitem__(key, value)

    def output_junos(self):
        """
        Output the modifiers to the only supported format!
        """
        keys = self.keys()
        keys.sort()
        return [k + (self[k] and ' '+str(self[k]) or '') + ';' for k in keys]

class RangeList(object):
    """
    A type which stores ordered sets, with efficient handling of
    ranges.  It can also store non-incrementable terms as an sorted set
    without collapsing into ranges.

    This is currently used to just store match conditions (e.g. protocols,
    ports), but could be fleshed out into a general-purpose class.  One
    thing to think about is how/whether to handle a list of tuples as distinct
    from a list of ranges.  Should we just store them as xrange objects?
    Should the object appear as discrete elements by default, for example
    in len(), with the collapsed view as a method, or should we keep it
    as it is now?  All the current uses of this class are in this file
    and have unit tests, so when we decided what the semantics of the
    generalized module ought to be, we can make it so without worry.
    """
    # Another way to implement this would be as a radix tree.
    def __init__(self, data=None):
        if data is None:
            data = []

        self.data = data
        self._do_collapse()


    def _cleanup(self, L):
        """
        Prepare a potential list of lists, tuples, digits for collapse. Does
        the following::

        1. Sort & Convert all inner lists to tuples
        2. Convert all tuples w/ only 1 item into single item
        3. Gather all single digits
        4. Convert to set to remove duplicates
        5. Return as a sorted list

        """
        ret = []

        # Get all list/tuples and return tuples
        tuples = [tuple(sorted(i)) for i in L if isinstance(i, (list, tuple))]
        singles = [i[0] for i in tuples if len(i) == 1] # Grab len of 1
        tuples = [i for i in tuples if len(i) == 2]     # Filter out len of 1
        digits = [i for i in L if isinstance(i, int)]   # Get digits

        ret.extend(singles)
        ret.extend(tuples)
        ret.extend(digits)

        if not ret:
            ret = L

        return sorted(set(ret))

    def _collapse(self, l):
        """
        Reduce a sorted list of elements to ranges represented as tuples;
        e.g. [1, 2, 3, 4, 10] -> [(1, 4), 10]
        """
        l = self._cleanup(l) # Remove duplicates

        # Don't bother reducing a single item
        if len(l) <= 1:
            return l

        # Make sure the elements are incrementable, or we can't reduce at all.
        try:
            l[0] + 1
        except (TypeError, AttributeError):
            return l
        '''
            try:
                l[0][0] + 1
            except (TypeError, AttributeError):
                return l
        '''

        # This last step uses a loop instead of pure functionalism because
        # it will be common to step through it tens of thousands of times,
        # for example in the case of (1024, 65535).
        # [x, x+1, ..., x+n] -> [(x, x+n)]
        n = 0
        try:
            while l[n] + 1 == l[n+1]:
                n += 1
        except IndexError:  # entire list collapses to one range
            return [(l[0], l[-1])]
        if n == 0:
            return [l[0]] + self._collapse(l[1:])
        else:
            return [(l[0], l[n])] + self._collapse(l[n+1:])

    def _do_collapse(self):
        self.data = self._collapse(self._expand(self.data))

    def _expand(self, l):
        """Expand a list of elements and tuples back to discrete elements.
        Opposite of _collapse()."""
        if not l:
            return l
        try:
            return range(l[0][0], l[0][1]+1) + self._expand(l[1:])
        except AttributeError:        # not incrementable
            return l
        except (TypeError, IndexError):
            return [l[0]] + self._expand(l[1:])

    def expanded(self):
        """Return a list with all ranges converted to discrete elements."""
        return self._expand(self.data)

    def __add__(self, y):
        for elt in y:
            self.append(elt)

    def append(self, obj):
        # We could make this faster.
        self.data.append(obj)
        self._do_collapse()

    def __cmp__(self, other):
        other = self._collapse(other)
        if self.data < other:
            return -1
        elif self.data > other:
            return 0
        else:
            return 0
# Classes
    'Remark',

    def __contains__(self, obj):
        """
        Performs voodoo to compare the following:
            * Compare single ports to tuples (i.e. 1700 in (1700, 1800))
            * Compare tuples to tuples (i.e. (1700,1800) in (0,65535))
            * Comparing tuple to integer ALWAYS returns False!!
        """
        for elt in self.data:
            if isinstance(elt, tuple):
                if isinstance(obj, tuple):
                    ## if obj is a tuple, see if it is within the range of elt
                    ## using xrange here is faster (add +1 to include elt[1])
                    ## otherwise you end up 1 digit short of max
                    rng = xrange(elt[0], elt[1] + 1)
                    if obj[0] in rng and obj[1] in rng:
                        return True
                else:
                    if elt[0] <= obj <= elt[1]:
                        return True

            elif hasattr(elt, '__contains__'):
                if obj in elt:
                    return True
            else:
                if elt == obj:
                    return True
        return False

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, str(self.data))

    def __str__(self):
        return str(self.data)

    # Straight passthrough of these:
    def __hash__(self):
        return self.data.__hash__(self.data)
    def __len__(self):
        return len(self.data)
    def __getitem__(self, key):
        return self.data[key]
    def __setitem__(self, key, value):
        self.data[key] = value
    def __delitem__(self, key):
        del self.data[key]
    def __iter__(self):
        return self.data.__iter__()

class TIP(IPy.IP):
    """
    Class based on IPy.IP, but with extensions for Trigger.

    Currently, only the only extension is the ability to negate a network
    block. Only used internally within the parser, as it's not complete
    (doesn't interact well with IPy.IP objects). Does not handle IPv6 yet.
    """
    def __init__(self, data, **kwargs):
        # Insert logic to handle 'except' preserve negated flag if it exists
        # already
        negated = getattr(data, 'negated', False)

        # Handle 'inactive:' address objects by setting inactive flag
        inactive = getattr(data, 'inactive', False)

        # Is data a string?
        if isinstance(data, (str, unicode)):
            d = data.split()
            # This means we got something like "1.2.3.4 except" or "inactive:
            # 1.2.3.4'
            if len(d) == 2:
                # Check if last word is 'except', set negated=True
                if d[-1] == 'except':
                    negated = True
                    data = d[0]
                # Check if first word is 'inactive:', set inactive=True
                elif d[0] == 'inactive:':
                    inactive = True
                    data = d[1]
            elif len(d) == 3:
                if d[-1] == 'except':
                    negated = True
                if d[0] == 'inactive:':
                    inactive = True
                if inactive and negated:
                    data = d[1]

        self.negated = negated # Set 'negated' variable
        self.inactive = inactive # Set 'inactive' variable
        IPy.IP.__init__(self, data, **kwargs)

        # Make it print prefixes for /32, /128 if we're negated or inactive (and
        # therefore assuming we're being used in a Juniper ACL.)
        if self.negated or self.inactive:
            self.NoPrefixForSingleIp = False

    def __cmp__(self, other):
        # Regular IPy sorts by prefix length before network base, but Juniper
        # (our baseline) does not. We also need comparisons to be different for
        # negation. Following Juniper's sorting, use I Pcompare, and then break
        # ties where negated < not negated.
        diff = cmp(self.ip, other.ip)
        if diff == 0:
            # If the same IP, compare by prefixlen
            diff = cmp(self.prefixlen(), other.prefixlen())
        # If both negated, they're the same
        if self.negated == other.negated:
            return diff
        # Sort to make negated < not negated
        if self.negated:
            diff = -1
        else:
            diff = 1
        # Return the base comparison
        return diff

    def __repr__(self):
        # Just stick an 'except' at the end if except is set since we don't
        # code to accept this in the constructor really just provided, for now,
        # as a debugging aid.
        rs = IPy.IP.__repr__(self)
        if self.negated:
            # Insert ' except' into the repr. (Yes, it's a hack!)
            rs = rs.split("'")
            rs[1] += ' except'
            rs = "'".join(rs) # Restore original repr
        if self.inactive:
            # Insert 'inactive: ' into the repr. (Yes, it's also a hack!)
            rs = rs.split("'")
            rs[1] = 'inactive: ' + rs[1]
            rs = "'".join(rs) # Restore original repr
        return rs

    def __str__(self):
        # IPy is not a new-style class, so the following doesn't work:
        # return super(TIP, self).__str__()
        rs = IPy.IP.__str__(self)
        if self.negated:
            rs += ' except'
        if self.inactive:
            rs = 'inactive: ' + rs
        return rs

    def __contains__(self, item):
        """
        Containment logic, including except.
        """
        item = TIP(item)
        # Calculate XOR
        xor = self.negated ^ item.negated
        # If one item is negated, it's never contained.
        if xor:
            return False
        matched = IPy.IP.__contains__(self, item)
        return matched ^ self.negated

class Comment(object):
    """
    Container for inline comments.
    """
    def __init__(self, data):
        self.data = data

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, repr(self.data))

    def __str__(self):
        return self.data

    def __len__(self):
        '''Defining this method allows null comments to be false.'''
        return len(self.data)

    def __iter__(self):
        return self.data.__iter__()

    def __contains__(self, item):
        return item in self.data

    def output_junos(self):
        """Output the Comment to JunOS format."""
        return '/*%s*/' % self.data

    def output_ios(self):
        """Output the Comment to IOS traditional format."""
        if not self.data:
            return '!'

        data = self.data
        if data.startswith('!'):
            prefix = '!'
            data = prefix + data
        else:
            prefix = '! '
        lines = data.splitlines()

        return '\n'.join(prefix + line for line in lines)

    def output_ios_named(self):
        """Output the Comment to IOS named format."""
        return self.output_ios()

    def output_iosxr(self):
        """Output the Comment to IOS XR format."""
        return self.output_ios()

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

class Term(object):
    """An individual term from which an ACL is made"""
    def __init__(self, name=None, action='accept', match=None, modifiers=None,
                 inactive=False, isglobal=False, extra=None):
        self.name = name
        self.action = action
        self.inactive = inactive
        self.isglobal = isglobal
        self.extra = extra
        self.makediscard = False # set to True if 'make discard' is used
        if match is None:
            self.match = Matches()
        else:
            self.match = match

        if modifiers is None:
            self.modifiers = Modifiers()
        else:
            self.modifiers = modifiers

        global Comments
        self.comments = Comments
        Comments = []

    def __repr__(self):
        return '<Term: %s>' % self.name

    def getname(self):
        return self.__name

    def setname(self, name):
        check_name(name, exceptions.BadTermName)
        self.__name = name

    def delname(self):
        self.name = None
    name = property(getname, setname, delname)

    def getaction(self):
        return self.__action

    def setaction(self, action):
        if action is None:
            action = 'accept'
        if action == 'next term':
            action = ('next', 'term')
        if isinstance(action, str):
            action = (action,)
        if len(action) > 2:
            raise exceptions.ActionError('too many arguments to action "%s"' %
                                         str(action))
        action = tuple(action)
        if action in (('accept',), ('discard',), ('reject',), ('next', 'term')):
            self.__action = action
        elif action == ('permit',):
            self.__action = ('accept',)
        elif action == ('deny',):
            self.__action = ('reject',)
        elif action[0] == 'reject':
            if action[1] not in icmp_reject_codes:
                raise exceptions.BadRejectCode('invalid rejection code ' + action[1])
            if action[1] == icmp_reject_codes[0]:
                action = ('reject',)
            self.__action = action
        elif action[0] == 'routing-instance':
            check_name(action[1], exceptions.BadRoutingInstanceName)
            self.__action = action
        else:
            raise exceptions.UnknownActionName('unknown action "%s"' % str(action))

    def delaction(self):
        self.action = 'accept'
    action = property(getaction, setaction, delaction)

    def set_action_or_modifier(self, action):
        """
        Add or replace a modifier, or set the primary action. This method exists
        for the convenience of parsers.
        """
        try:
            self.action = action
        except exceptions.UnknownActionName:
            if not isinstance(action, tuple):
                self.modifiers[action] = None
            else:
                if len(action) == 1:
                    self.modifiers[action[0]] = None
                else:
                    self.modifiers[action[0]] = action[1]

    def output(self, format, *largs, **kwargs):
        """
        Output the term to the specified format

        :param format: The desired output format.
        """
        return getattr(self, 'output_' + format)(*largs, **kwargs)

    def output_junos(self, *args, **kwargs):
        """Convert the term to JunOS format."""
        if self.name is None:
            raise exceptions.MissingTermName('JunOS requires terms to be named')
        out = ['%sterm %s {' %
                (self.inactive and 'inactive: ' or '', self.name)]
        out += ['    ' + c.output_junos() for c in self.comments if c]
        if self.extra:
            blah = str(self.extra)
            out += "/*",blah,"*/"
        if self.match:
            out.append('    from {')
            out += [' '*8 + x for x in self.match.output_junos()]
            out.append('    }')
        out.append('    then {')
        acttext = '        %s;' % ' '.join(self.action)
        # add a comment if 'make discard' is in use
        if self.makediscard:
            acttext += (" /* REALLY AN ACCEPT, MODIFIED BY"
                        " 'make discard' ABOVE */")
        out.append(acttext)
        out += [' '*8 + x for x in self.modifiers.output_junos()]
        out.append('    }')
        out.append('}')
        return out

    def _ioslike(self, prefix=''):
        if self.inactive:
            raise exceptions.VendorSupportLacking("inactive terms not supported by IOS")
        action = ''
        if self.action == ('accept',):
            action = 'permit '
        #elif self.action == ('reject',):
        elif self.action in (('reject',), ('discard',)):
            action = 'deny '
        else:
            raise VendorSupportLacking('"%s" action not supported by IOS' % ' '.join(self.action))
        suffix = ''
        for k, v in self.modifiers.iteritems():
            if k == 'syslog':
                suffix += ' log'
            elif k == 'count':
                pass        # counters are implicit in IOS
            else:
                raise exceptions.VendorSupportLacking('"%s" modifier not supported by IOS' % k)
        return [prefix + action + x + suffix for x in self.match.output_ios()]

    def output_ios(self, prefix=None, acl_name=None):
        """
        Output term to IOS traditional format.

        :param prefix: Prefix to use, default: 'access-list'
        :param acl_name: Name of access-list to display
        """
        comments = [c.output_ios() for c in self.comments]
        # If prefix isn't set, but name is, force the template
        if prefix is None and acl_name is not None:
            prefix = 'access-list %s ' % acl_name

        # Or if prefix is set, but acl_name isn't, make sure prefix ends with ' '
        elif prefix is not None and acl_name is None:
            if not prefix.endswith(' '):
                prefix += ' '

        # Or if both are set, use them
        elif prefix is not None and acl_name is not None:
            prefix = '%s %s ' % (prefix.strip(), acl_name.strip())

        # Otherwise no prefix
        else:
            prefix = ''

        return comments + self._ioslike(prefix)

    def output_ios_named(self, prefix='', *args, **kwargs):
        """Output term to IOS named format."""
        comments = [c.output_ios_named() for c in self.comments]
        return comments + self._ioslike(prefix)

    def output_iosxr(self, prefix='', *args, **kwargs):
        """Output term to IOS XR format."""
        comments = [c.output_iosxr() for c in self.comments]
        return comments + self._ioslike(prefix)

class TermList(list):
    """Container class for Term objects within an ACL object."""
    pass

class Protocol(object):
    """
    A protocol object used for access membership tests in :class:`Term` objects.
    Acts like an integer, but stringify into a name if possible.
    """
    num2name = {
        1: 'icmp',
        2: 'igmp',
        4: 'ipip',
        6: 'tcp',
        8: 'egp',
        17: 'udp',
        41: 'ipv6',
        #46: 'rsvp',
        47: 'gre',
        50: 'esp',
        51: 'ah',
        89: 'ospf',
        94: 'nos',
        103: 'pim',
        #112: 'vrrp' # Breaks Cisco compatibility
    }

    name2num = dict([(v, k) for k, v in num2name.iteritems()])
    name2num['ahp'] = 51    # undocumented Cisco special name

    def __init__(self, arg):
        if isinstance(arg, Protocol):
            self.value = arg.value
        elif arg in Protocol.name2num:
            self.value = Protocol.name2num[arg]
        else:
            self.value = int(arg)

    def __str__(self):
        if self.value in Protocol.num2name:
            return Protocol.num2name[self.value]
        else:
            return str(self.value)

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, str(self))

    def __cmp__(self, other):
        '''Protocol(6) == 'tcp' == 6 == Protocol('6').'''
        return self.value.__cmp__(Protocol(other).value)

    def __hash__(self):
        return hash(self.value)

    def __getattr__(self, name):
        '''Allow arithmetic operations to work.'''
        return getattr(self.value, name)

class Matches(MyDict):
    """
    Container class for Term.match object used for membership tests on
    access checks.
    """
    def __setitem__(self, key, arg):
        if key in ('ah-spi', 'destination-mac-address', 'ether-type',
                   'esp-spi', 'forwarding-class', 'interface-group',
                   'source-mac-address', 'vlan-ether-type',
                   'fragment-flags', 'source-class', 'destination-class'):
            raise NotImplementedError('match on %s not implemented' % key)

        if arg is None:
            raise exceptions.MatchError('match must have an argument')

        negated = False
        if key.endswith('-except'):
            negated = True
            key = key[:-7]

        if key in ('port', 'source-port', 'destination-port'):
            arg = map(do_port_lookup, arg)
            check_range(arg, 0, 65535)
        elif key == 'protocol':
            arg = map(do_protocol_lookup, arg)
            check_range(arg, 0, 255)
        elif key == 'fragment-offset':
            arg = map(do_port_lookup, arg)
            check_range(arg, 0, 8191)
        elif key == 'icmp-type':
            arg = map(do_icmp_type_lookup, arg)
            check_range(arg, 0, 255)
        elif key == 'icmp-code':
            arg = map(do_icmp_code_lookup, arg)
            check_range(arg, 0, 255)
        elif key == 'icmp-type-code':
            # Not intended for external use; this is for parser convenience.
            self['icmp-type'] = [arg[0]]
            try:
                self['icmp-code'] = [arg[1]]
            except IndexError:
                try:
                    del self['icmp-code']
                except KeyError:
                    pass
            return
        elif key == 'packet-length':
            arg = map(int, arg)
            check_range(arg, 0, 65535)
        elif key in ('address', 'source-address', 'destination-address'):
            arg = map(TIP, arg)
        elif key in ('prefix-list', 'source-prefix-list',
                     'destination-prefix-list'):
            for pl in arg:
                check_name(pl, exceptions.MatchError)
        elif key in tcp_flag_specials:
            # This cannot be the final form of how to represent tcp-flags.
            # Instead, we need to implement a real parser for it.
            # See: http://www.juniper.net/techpubs/software/junos/junos73/swconfig73-policy/html/firewall-config14.html
            arg = [tcp_flag_specials[key]]
            key = 'tcp-flags'
        elif key == 'tcp-flags':
            pass
        elif key == 'ip-options':
            arg = map(do_ip_option_lookup, arg)
            check_range(arg, 0, 255)
        elif key in ('first-fragment', 'is-fragment'):
            arg = []
        elif key == 'dscp':
            pass
        elif key == 'precedence':
            pass
        else:
            raise exceptions.UnknownMatchType('unknown match type "%s"' % key)

        arg = RangeList(arg)

        replacing = [key, key+'-except']
        for type in ('port', 'address', 'prefix-list'):
            if key == type:
                for sd in ('source', 'destination'):
                    replacing += [sd+'-'+type, sd+'-'+type+'-except']
        for k in replacing:
            try: del self[k]
            except KeyError: pass
        if (negated):
            super(Matches, self).__setitem__(key + '-except', arg)
        else:
            super(Matches, self).__setitem__(key, arg)

    def junos_str(self, pair):
        """
        Convert a 2-tuple into a hyphenated string, e.g. a range of ports. If
        not a tuple, tries to treat it as IPs or failing that, casts it to a
        string.

        :param pair:
            The 2-tuple to convert.
        """
        try:
            return '%s-%s' % pair # Tuples back to ranges.
        except TypeError:
            try:
                # Make it print prefixes for /32, /128
                pair.NoPrefixForSingleIp = False
            except AttributeError:
                pass
        return str(pair)

    def ios_port_str(self, ports):
        """
        Convert a list of tuples back to ranges, then to strings.

        :param ports:
            A list of port tuples, e.g. [(0,65535), (1,2)].
        """
        a = []
        for port in ports:
            try:
                if port[0] == 0:
                    # Omit ports if 0-65535
                    if port[1] == 65535:
                        continue
                    a.append('lt %s' % (port[1]+1))
                elif port[1] == 65535:
                    a.append('gt %s' % (port[0]-1))
                else:
                    a.append('range %s %s' % port)
            except TypeError:
                a.append('eq %s' % str(port))
        return a

    def ios_address_str(self, addrs):
        """
        Convert a list of addresses to IOS-style stupid strings.

        :param addrs:
            List of IP address objects.
        """
        a = []
        for addr in addrs:
            # xxx flag negated addresses?
            if addr.negated:
                raise exceptions.VendorSupportLacking(
                    'negated addresses are not supported in IOS')
            if addr.prefixlen() == 0:
                a.append('any')
            elif addr.prefixlen() == 32:
                a.append('host %s' % addr.net())
            else:
                inverse_mask = make_inverse_mask(addr.prefixlen())
                a.append('%s %s' % (addr.net(), inverse_mask))
        return a

    def output_junos(self):
        """Return a list that can form the ``from { ... }`` clause of the term."""
        a = []
        keys = self.keys()
        keys.sort(lambda x, y: cmp(junos_match_order[x], junos_match_order[y]))
        for s in keys:
            matches = map(self.junos_str, self[s])
            has_negated_addrs = any(m for m in matches if m.endswith(' except'))
            if s in address_matches:
                # Check to see if any of the added is any, and if so break out,
                # but only if none of the addresses is "negated".
                if '0.0.0.0/0' in matches and not has_negated_addrs:
                    continue
                a.append(s + ' {')
                a += ['    ' + x + ';' for x in matches]
                a.append('}')
                continue
            if s == 'tcp-flags' and len(self[s]) == 1:
                try:
                    a.append(tcp_flag_rev[self[s][0]] + ';')
                    continue
                except KeyError:
                    pass
            if len(matches) == 1:
                s += ' ' + matches[0]
            elif len(matches) > 1:
                s += ' [ ' + ' '.join(matches) + ' ]'
            a.append(s + ';')
        return a

    def output_ios(self):
        """Return a string of IOS ACL bodies."""
        # This is a mess!  Thanks, Cisco.
        protos = []
        sources = []
        dests = []
        sourceports = []
        destports = []
        trailers = []
        for key, arg in self.iteritems():
            if key == 'source-port':
                sourceports += self.ios_port_str(arg)
            elif key == 'destination-port':
                destports += self.ios_port_str(arg)
            elif key == 'source-address':
                sources += self.ios_address_str(arg)
            elif key == 'destination-address':
                dests += self.ios_address_str(arg)
            elif key == 'protocol':
                protos += map(str, arg)
            elif key == 'icmp-type':
                for type in arg.expanded():
                    if 'icmp-code' in self:
                        for code in self['icmp-code']:
                            try:
                                destports.append(ios_icmp_names[(type, code)])
                            except KeyError:
                                destports.append('%d %d' % (type, code))
                    else:
                        try:
                            destports.append(ios_icmp_names[(type,)])
                        except KeyError:
                            destports.append(str(type))
            elif key == 'icmp-code':
                if 'icmp-type' not in self:
                    raise exceptions.VendorSupportLacking('need ICMP code w/type')
            elif key == 'tcp-flags':
                if arg != [tcp_flag_specials['tcp-established']]:
                    raise exceptions.VendorSupportLacking('IOS supports only "tcp-flags established"')
                trailers += ['established']
            else:
                raise exceptions.VendorSupportLacking('"%s" not in IOS' % key)
        if not protos:
            protos = ['ip']
        if not sources:
            sources = ['any']
        if not dests:
            dests = ['any']
        if not sourceports:
            sourceports = ['']
        if not destports:
            destports = ['']
        if not trailers:
            trailers = ['']
        a = []

        # There is no mercy in this Dojo!!
        for proto in protos:
            for source in sources:
                for sourceport in sourceports:
                    for dest in dests:
                        for destport in destports:
                            for trailer in trailers:
                                s = proto + ' ' + source
                                if sourceport:
                                    s += ' ' + sourceport
                                s += ' ' + dest
                                if destport:
                                    s += ' ' + destport
                                if trailer:
                                    s += ' ' + trailer
                                a.append(s)
        return a
