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


# Proceed at your own risk. It's kind of a mess from here on out!
icmp_reject_codes = (
    'administratively-prohibited',
    'bad-host-tos',
    'bad-network-tos',
    'host-prohibited',
    'host-unknown',
    'host-unreachable',
    'network-prohibited',
    'network-unknown',
    'network-unreachable',
    'port-unreachable',
    'precedence-cutoff',
    'precedence-violation',
    'protocol-unreachable',
    'source-host-isolated',
    'source-route-failed',
    'tcp-reset')

icmp_types = {
    'echo-reply': 0,
    'echo-request': 8,
    'echo': 8,                # undocumented
    'info-reply': 16,
    'info-request': 15,
    'information-reply': 16,
    'information-request': 15,
    'mask-request': 17,
    'mask-reply': 18,
    'parameter-problem': 12,
    'redirect': 5,
    'router-advertisement': 9,
    'router-solicit': 10,
    'source-quench': 4,
    'time-exceeded': 11,
    'timestamp': 13,
    'timestamp-reply': 14,
    'unreachable': 3}

icmp_codes = {
    'ip-header-bad': 0,
    'required-option-missing': 1,
    'redirect-for-host': 1,
    'redirect-for-network': 0,
    'redirect-for-tos-and-host': 3,
    'redirect-for-tos-and-net': 2,
    'ttl-eq-zero-during-reassembly': 1,
    'ttl-eq-zero-during-transit': 0,
    'communication-prohibited-by-filtering': 13,
    'destination-host-prohibited': 10,
    'destination-host-unknown': 7,
    'destination-network-prohibited': 9,
    'destination-network-unknown': 6,
    'fragmentation-needed': 4,
    'host-precedence-violation': 14,
    'host-unreachable': 1,
    'host-unreachable-for-TOS': 12,
    'network-unreachable': 0,
    'network-unreachable-for-TOS': 11,
    'port-unreachable': 3,
    'precedence-cutoff-in-effect': 15,
    'protocol-unreachable': 2,
    'source-host-isolated': 8,
    'source-route-failed': 5}

# Cisco "ICMP message type names and ICMP message type and code names" from
# IOS 12.0 documentation.  Verified these against actual practice of 12.1(21),
# since documentation is incomplete.  For example, is 'echo' code 8, type 0
# or code 8, type any?  Experiment shows that it is code 8, type any.
ios_icmp_messages = {
    'administratively-prohibited': (3, 13),
    'alternate-address': (6,),
    'conversion-error': (31,),
    'dod-host-prohibited': (3, 10),
    'dod-net-prohibited': (3, 9),
    'echo': (8,),
    'echo-reply': (0,),
    'general-parameter-problem': (12, 0),
    'host-isolated': (3, 8),
    'host-precedence-unreachable': (3, 14),
    'host-redirect': (5, 1),
    'host-tos-redirect': (5, 3),
    'host-tos-unreachable': (3, 12),
    'host-unknown': (3, 7),
    'host-unreachable': (3, 1),
    'information-reply': (16,),
    'information-request': (15,),
    'mask-reply': (18,),
    'mask-request': (17,),
    'mobile-redirect': (32,),
    'net-redirect': (5, 0),
    'net-tos-redirect': (5, 2),
    'net-tos-unreachable': (3, 11),
    'net-unreachable': (3, 0),
    'network-unknown': (3, 6),
    'no-room-for-option': (12, 2),
    'option-missing': (12, 1),
    'packet-too-big': (3, 4),
    'parameter-problem': (12,),
    'port-unreachable': (3, 3),
    'precedence-unreachable': (3, 14),                # not (3, 15)
    'protocol-unreachable': (3, 2),
    'reassembly-timeout': (11, 1),                # not (11, 2)
    'redirect': (5,),
    'router-advertisement': (9,),
    'router-solicitation': (10,),
    'source-quench': (4,),
    'source-route-failed': (3, 5),
    'time-exceeded': (11,),
    'timestamp-reply': (14,),
    'timestamp-request': (13,),
    'traceroute': (30,),
    'ttl-exceeded': (11, 0),
    'unreachable': (3,) }
ios_icmp_names = dict([(v, k) for k, v in ios_icmp_messages.iteritems()])

# Not all of these are in /etc/services even as of RHEL 4; for example, it
# has 'syslog' only in UDP, and 'dns' as 'domain'.  Also, Cisco (according
# to the IOS 12.0 documentation at least) allows 'dns' in UDP and not TCP,
# along with other anomalies.  We'll be somewhat more generous in parsing
# input, and always output as integers.
ports = {
    'afs': 1483,        # JunOS
    'bgp': 179,
    'biff': 512,
    'bootpc': 68,
    'bootps': 67,
    'chargen': 19,
    'cmd': 514,                # undocumented IOS
    'cvspserver': 2401,        # JunOS
    'daytime': 13,
    'dhcp': 67,                # JunOS
    'discard': 9,
    'dns': 53,
    'dnsix': 90,
    'domain': 53,
    'echo': 7,
    'eklogin': 2105,        # JunOS
    'ekshell': 2106,        # JunOS
    'exec': 512,        # undocumented IOS
    'finger': 79,
    'ftp': 21,
    'ftp-data': 20,
    'gopher': 70,
    'hostname': 101,
    'http': 80,                # JunOS
    'https': 443,        # JunOS
    'ident': 113,        # undocumented IOS
    'imap': 143,        # JunOS
    'irc': 194,
    'isakmp': 500,        # undocumented IOS
    'kerberos-sec': 88,        # JunOS
    'klogin': 543,
    'kpasswd': 761,        # JunOS
    'kshell': 544,
    'ldap': 389,        # JunOS
    'ldp': 646,                # undocumented JunOS
    'login': 513,        # JunOS
    'lpd': 515,
    'mobile-ip': 434,
    'mobileip-agent': 434,  # JunOS
    'mobileip-mn': 435,        # JunOS
    'msdp': 639,        # JunOS
    'nameserver': 42,
    'netbios-dgm': 138,
    'netbios-ns': 137,
    'netbios-ssn': 139,        # JunOS
    'nfsd': 2049,        # JunOS
    'nntp': 119,
    'ntalk': 518,        # JunOS
    'ntp': 123,
    'pop2': 109,
    'pop3': 110,
    'pptp': 1723,        # JunOS
    'printer': 515,        # JunOS
    'radacct': 1813,        # JunOS
    'radius': 1812,        # JunOS and undocumented IOS
    'rip': 520,
    'rkinit': 2108,        # JunOS
    'smtp': 25,
    'snmp': 161,
    'snmptrap': 162,
    'snmp-trap': 162,        # undocumented IOS
    'snpp': 444,        # JunOS
    'socks': 1080,        # JunOS
    'ssh': 22,                # JunOS
    'sunrpc': 111,
    'syslog': 514,
    'tacacs': 49,        # undocumented IOS
    'tacacs-ds': 49,
    'talk': 517,
    'telnet': 23,
    'tftp': 69,
    'time': 37,
    'timed': 525,        # JunOS
    'uucp': 540,
    'who': 513,
    'whois': 43,
    'www': 80,
    'xdmcp': 177,
    'zephyr-clt': 2103,        # JunOS
    'zephyr-hm': 2104        # JunOS
}

dscp_names = {
    'be': 0,
    'cs0': 0,
    'cs1': 8,
    'af11': 10,
    'af12': 12,
    'af13': 14,
    'cs2': 16,
    'af21': 18,
    'af22': 20,
    'af23': 22,
    'cs3': 24,
    'af31': 26,
    'af32': 28,
    'af33': 30,
    'cs4': 32,
    'af41': 34,
    'af42': 36,
    'af43': 38,
    'cs5': 40,
    'ef': 46,
    'cs6': 48,
    'cs7': 56
}

precedence_names = {
    'critical-ecp': 0xa0,        # JunOS
    'critical': 0xa0,                # IOS
    'flash': 0x60,
    'flash-override': 0x80,
    'immediate': 0x40,
    'internet-control': 0xc0,        # JunOS
    'internet': 0xc0,                # IOS
    'net-control': 0xe0,        # JunOS
    'network': 0xe0,                # IOS
    'priority': 0x20,
    'routine': 0x00 }

ip_option_names = {
    'loose-source-route': 131,
    'record-route': 7,
    'router-alert': 148,
    'strict-source-route': 137,
    'timestamp': 68 }

fragment_flag_names = {
    'dont-fragment': 0x4000,
    'more-fragments': 0x2000,
    'reserved': 0x8000 }

tcp_flag_names = {
    'ack': 0x10,
    'fin': 0x01,
    'push': 0x08,
    'rst': 0x04,
    'syn': 0x02,
    'urgent': 0x20 }

tcp_flag_specials = {
    'tcp-established': '"ack | rst"',
    'tcp-initial': '"syn & !ack"' }
tcp_flag_rev = dict([(v, k) for k, v in tcp_flag_specials.iteritems()])

adrsbk = { 'svc':{'group':{}, 'book':{}}, 'addr':{'group':{},'book':{}} }

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


# Temporary resting place for comments, so the rest of the parser can
# ignore them.  Yes, this makes the library not thread-safe.
Comments = []


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
        # Is data a string?
        if isinstance(data, (str, unicode)):
            d = data.split()
            if len(d) == 2 and d[-1] == 'except':
                negated = True
                data = d[0]
        self.negated = negated # Set 'negated' variable
        IPy.IP.__init__(self, data, **kwargs)

        # Make it print prefixes for /32, /128 if we're negated (and therefore
        # assuming we're being used in a Juniper ACL.
        if self.negated:
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
        return rs

    def __str__(self):
        # IPy is not a new-style class, so the following doesn't work:
        # return super(TIP, self).__str__()
        rs = IPy.IP.__str__(self)
        if self.negated:
            rs += ' except'
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

class Remark(Comment):
    """
    IOS extended ACL "remark" lines automatically become comments when
    converting to other formats of ACL.
    """
    def output_ios_named(self):
        """Output the Remark to IOS named format."""
        return ' remark ' + self.data

class PolicerGroup(object):
    """Container for Policer objects. Juniper only."""
    def __init__(self, format=None):
        self.policers = []
        self.format   = format
        global Comments
        self.comments = Comments
        Comments = []

    def output(self, format=None, *largs, **kwargs):
        if format is None:
            format = self.format
        return getattr(self,'output_' + format)(*largs, **kwargs)

    def output_junos(self, replace=False):
        output = []
        for ent in self.policers:
            for x in ent.output():
                output.append(x)

        if replace:
            return ['firewall {', 'replace:'] + ['    '+x for x in output] + ['}']
        else:
            return output

class ACL(object):
    """
    An abstract access-list object intended to be created by the :func:`parse`
    function.
    """
    def __init__(self, name=None, terms=None, format=None, family=None):
        check_name(name, exceptions.ACLNameError, max_len=24)
        self.name = name
        self.family = family
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

class Policer(object):
    """
    Container class for policer policy definitions. This is a dummy class for
    now, that just passes it through as a string.
    """
    def __init__(self, name, data):
        if not name:
            raise exceptions.ActionError("Policer requres name")
        self.name = name
        self.exceedings = []
        self.actions    = []
        for elt in data:
            for k,v in elt.iteritems():
                if k == 'if-exceeding':
                    for entry in v:
                        type, value = entry
                        if type == 'bandwidth-limit':
                            limit = self.str2bits(value)
                            if limit > 32000000000 or limit < 32000:
                                raise "bandwidth-limit must be between 32000bps and 32000000000bps"
                            self.exceedings.append((type, limit))
                        elif type == 'burst-size-limit':
                            limit = self.str2bits(value)
                            if limit > 100000000 or limit < 1500:
                                raise "burst-size-limit must be between 1500B and 100,000,000B"
                            self.exceedings.append((type, limit))
                        elif type == 'bandwidth-percent':
                            limit = int(value)
                            if limit < 1 or limit > 100:
                                raise "bandwidth-percent must be between 1 and 100"
                        else:
                            raise "Unknown policer if-exceeding tag: %s" % type
                elif k == 'action':
                    for i in v:
                        self.actions.append(i)

    def str2bits(self, str):
        try:
            val = int(str)
        except:
            if str[-1] == 'k':
                return int(str[0:-1]) * 1024
            if str[-1] == 'm':
                return int(str[0:-1]) * 1048576
            else:
                raise "invalid bit definition %s" % str
        return val

    def __repr__(self):
            return '<%s: %s>' % (self.__class__.__name__, repr(self.name))

    def __str__(self):
            return self.data

    def output(self):
        output = ['policer %s {' % self.name]
        if self.exceedings:
            output.append('    if-exceeding {')
        for x in self.exceedings:
            output.append('        %s %s;' % (x[0],x[1]))
        if self.exceedings:
            output.append('    }')
        if self.actions:
            output.append('    then {')
        for x in self.actions:
            output.append('        %s;' % x)

        if self.actions:
            output.append('    }')
        output.append('}')
        return output

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

def check_range(values, min, max):
    for value in values:
        try:
            for subvalue in value:
                check_range([subvalue], min, max)
        except TypeError:
            if not min <= value <= max:
                raise exceptions.BadMatchArgRange('match arg %s must be between %d and %d'
                                                  % (str(value), min, max))


# Ordering for JunOS match clauses.  AOL style rules:
# 1. Use the order found in the IP header, except, put protocol at the end
#    so it is close to the port and tcp-flags.
# 2. General before specific.
# 3. Source before destination.
junos_match_ordering_list = (
    'source-mac-address',
    'destination-mac-address',
    'packet-length',
    'fragment-flags',
    'fragment-offset',
    'first-fragment',
    'is-fragment',
    'prefix-list',
    'address',
    'source-prefix-list',
    'source-address',
    'destination-prefix-list',
    'destination-address',
    'ip-options',
    'protocol',
    # TCP/UDP
    'tcp-flags',
    'port',
    'source-port',
    'destination-port',
    # ICMP
    'icmp-code',
    'icmp-type' )

junos_match_order = {}

for i, match in enumerate(junos_match_ordering_list):
    junos_match_order[match] = i*2
    junos_match_order[match+'-except'] = i*2 + 1

# These types of Juniper matches go in braces, not square brackets.
address_matches = set(['address', 'destination-address', 'source-address', 'prefix-list', 'source-prefix-list', 'destination-prefix-list'])
for match in list(address_matches):
    address_matches.add(match+'-except')

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


#
# Here begins the parsing code.  Break this into another file?
#

# Each production can be any of:
# 1. string
#    if no subtags: -> matched text
#    if single subtag: -> value of that
#    if list: -> list of the value of each tag
# 2. (string, object) -> object
# 3. (string, callable_object) -> object(arg)

subtagged = set()
def S(prod):
    """
    Wrap your grammar token in this to call your helper function with a list
    of each parsed subtag, instead of the raw text. This is useful for
    performing modifiers.

    :param prod: The parser product.
    """
    subtagged.add(prod)
    return prod

def literals(d):
    '''Longest match of all the strings that are keys of 'd'.'''
    keys = [str(key) for key in d]
    keys.sort(lambda x, y: len(y) - len(x))
    return ' / '.join(['"%s"' % key for key in keys])

def update(d, **kwargs):
    # Check for duplicate subterms, which is legal but too confusing to be
    # allowed at AOL.  For example, a Juniper term can have two different
    # 'destination-address' clauses, which means that the first will be
    # ignored.  This led to an outage on 2006-10-11.
    for key in kwargs.iterkeys():
        if key in d:
            raise exceptions.ParseError('duplicate %s' % key)
    d.update(kwargs)
    return d

def dict_sum(dlist):
    dsum = {}
    for d in dlist:
        for k, v in d.iteritems():
            if k in dsum:
                dsum[k] += v
            else:
                dsum[k] = v
    return dsum

## syntax error messages
errs = {
    'comm_start': '"comment missing /* below line %(line)s"',
    'comm_stop':  '"comment missing */ below line %(line)s"',
    'default':    '"expected %(expected)s line %(line)s"',
    'semicolon':  '"missing semicolon on line %(line)s"',
}

rules = {
    'digits':     '[0-9]+',
    '<digits_s>': '[0-9]+',
    '<ts>':       '[ \\t]+',
    '<ws>':       '[ \\t\\n]+',
    '<EOL>':      "('\r'?,'\n')/EOF",
    'alphanums':  '[a-zA-Z0-9]+',
    'word':       '[a-zA-Z0-9_.-]+',
    'anychar':    "[ a-zA-Z0-9.$:()&,/'_-]",
    'hex':        '[0-9a-fA-F]+',
    'ipchars':    '[0-9a-fA-F:.]+',

    'ipv4':       ('digits, (".", digits)*', TIP),
    'ipaddr':     ('ipchars', TIP),
    'cidr':       ('(ipaddr / ipv4), "/", digits, (ws+, "except")?', TIP),
    'macaddr':    'hex, (":", hex)+',
    'protocol':   (literals(Protocol.name2num) + ' / digits',
                   do_protocol_lookup),
    'tcp':        ('"tcp" / "6"', Protocol('tcp')),
    'udp':        ('"udp" / "17"', Protocol('udp')),
    'icmp':       ('"icmp" / "1"', Protocol('icmp')),
    'icmp_type':  (literals(icmp_types) + ' / digits', do_icmp_type_lookup),
    'icmp_code':  (literals(icmp_codes) + ' / digits', do_icmp_code_lookup),
    'port':       (literals(ports) + ' / digits', do_port_lookup),
    'dscp':       (literals(dscp_names) + ' / digits', do_dscp_lookup),
    'root':       'ws?, junos_raw_acl / junos_replace_family_acl / junos_replace_acl / junos_replace_policers / ios_acl, ws?',
}


#
# IOS-like ACLs.
#


def make_inverse_mask(prefixlen):
    """
    Return an IP object of the inverse mask of the CIDR prefix.

    :param prefixlen:
        CIDR prefix
    """
    inverse_bits = 2 ** (32 - prefixlen) - 1
    return TIP(inverse_bits)


# Build a table to unwind Cisco's weird inverse netmask.
# TODO (jathan): These don't actually get sorted properly, but it doesn't seem
# to have mattered up until now. Worth looking into it at some point, though.
inverse_mask_table = dict([(make_inverse_mask(x), x) for x in range(0, 33)])

def handle_ios_match(a):
    protocol, source, dest = a[:3]
    extra = a[3:]

    match = Matches()
    modifiers = Modifiers()

    if protocol:
        match['protocol'] = [protocol]

    for sd, arg in (('source', source), ('destination', dest)):
        if isinstance(arg, list):
            if arg[0] is not None:
                match[sd + '-address'] = [arg[0]]
            match[sd + '-port'] = arg[1]
        else:
            if arg is not None:
                match[sd + '-address'] = [arg]

    if 'log' in extra:
        modifiers['syslog'] = True
        extra.remove('log')

    if protocol == 'icmp':
        if len(extra) > 2:
            raise NotImplementedError(extra)
        if extra and isinstance(extra[0], tuple):
            extra = extra[0]
        if len(extra) >= 1:
            match['icmp-type'] = [extra[0]]
        if len(extra) >= 2:
            match['icmp-code'] = [extra[1]]
    elif protocol == 'tcp':
        if extra == ['established']:
            match['tcp-flags'] = [tcp_flag_specials['tcp-established']]
        elif extra:
            raise NotImplementedError(extra)
    elif extra:
        raise NotImplementedError(extra)

    return {'match': match, 'modifiers': modifiers}

def handle_ios_acl(rows):
    acl = ACL()
    for d in rows:
        if not d:
            continue
        for k, v in d.iteritems():
            if k == 'no':
                acl = ACL()
            elif k == 'name':
                if acl.name:
                    if v != acl.name:
                        raise exceptions.ACLNameError("Name '%s' does not match ACL '%s'" % (v, acl.name))
                else:
                    acl.name = v
            elif k == 'term':
                acl.terms.append(v)
            elif k == 'format':
                acl.format = v
            # Brocade receive-acl
            elif k == 'receive_acl':
                acl.is_receive_acl = True
            else:
                raise RuntimeError('unknown key "%s" (value %s)' % (k, v))
    # In traditional ACLs, comments that belong to the first ACE are
    # indistinguishable from comments that belong to the ACL.
    #if acl.format == 'ios' and acl.terms:
    if acl.format in ('ios', 'ios_brocade') and acl.terms:
        acl.comments += acl.terms[0].comments
        acl.terms[0].comments = []
    return acl

unary_port_operators = {
    'eq':   lambda x: [x],
    'le':   lambda x: [(0, x)],
    'lt':   lambda x: [(0, x-1)],
    'ge':   lambda x: [(x, 65535)],
    'gt':   lambda x: [(x+1, 65535)],
    'neq':  lambda x: [(0, x-1), (x+1, 65535)]
}

rules.update({
    'ios_ip':                    'kw_any / host_ipv4 / ios_masked_ipv4',
    'kw_any':                    ('"any"', None),
    'host_ipv4':            '"host", ts, ipv4',
    S('ios_masked_ipv4'):   ('ipv4, ts, ipv4_inverse_mask',
                             lambda (net, length): TIP('%s/%d' % (net, length))),
    'ipv4_inverse_mask':    (literals(inverse_mask_table),
                             lambda x: inverse_mask_table[TIP(x)]),

    'kw_ip':                    ('"ip"', None),
    S('ios_match'):            ('kw_ip / protocol, ts, ios_ip, ts, ios_ip, '
                             '(ts, ios_log)?',
                             handle_ios_match),
    S('ios_tcp_port_match'):('tcp, ts, ios_ip_port, ts, ios_ip_port, '
                             '(ts, established)?, (ts, ios_log)?',
                             handle_ios_match),
    S('ios_udp_port_match'):('udp, ts, ios_ip_port, ts, ios_ip_port, '
                             '(ts, ios_log)?',
                             handle_ios_match),
    S('ios_ip_port'):            'ios_ip, (ts, unary_port / ios_range)?',
    S('unary_port'):            ('unary_port_operator, ts, port',
                             lambda (op, arg): unary_port_operators[op](arg)),
    'unary_port_operator':  literals(unary_port_operators),
    S('ios_range'):            ('"range", ts, port, ts, port',
                             lambda (x, y): [(x, y)]),
    'established':            '"established"',
    S('ios_icmp_match'):    ('icmp, ts, ios_ip, ts, ios_ip, (ts, ios_log)?, '
                             '(ts, ios_icmp_message / '
                             ' (icmp_type, (ts, icmp_code)?))?, (ts, ios_log)?',
                             handle_ios_match),
    'ios_icmp_message':     (literals(ios_icmp_messages),
                             lambda x: ios_icmp_messages[x]),

    'ios_action':            '"permit" / "deny"',
    'ios_log':                    '"log-input" / "log"',
    S('ios_action_match'):  ('ios_action, ts, ios_tcp_port_match / '
                             'ios_udp_port_match / ios_icmp_match / ios_match',
                             lambda x: {'term': Term(action=x[0], **x[1])}),

    'ios_acl_line':            'ios_acl_match_line / ios_acl_no_line',
    S('ios_acl_match_line'):('"access-list", ts, digits, ts, ios_action_match',
                             lambda x: update(x[1], name=x[0], format='ios')),
    S('ios_acl_no_line'):   ('"no", ts, "access-list", ts, digits',
                             lambda x: {'no': True, 'name': x[0]}),

    'ios_ext_line':          ('ios_action_match / ios_ext_name_line / '
                             'ios_ext_no_line / ios_remark_line / '
                             'ios_rebind_acl_line / ios_rebind_receive_acl_line'),
    S('ios_ext_name_line'): ('"ip", ts, "access-list", ts, '
                             '"extended", ts, word',
                             lambda x: {'name': x[0], 'format': 'ios_named'}),
    S('ios_ext_no_line'):   ('"no", ts, "ip", ts, "access-list", ts, '
                             '"extended", ts, word',
                             lambda x: {'no': True, 'name': x[0]}),
    # Brocade "ip rebind-acl foo" or "ip rebind-receive-acl foo" syntax
    S('ios_rebind_acl_line'): ('"ip", ts, "rebind-acl", ts, word',
                              lambda x: {'name': x[0], 'format': 'ios_brocade'}),

    # Brocade "ip rebind-acl foo" or "ip rebind-receive-acl foo" syntax
    S('ios_rebind_receive_acl_line'): ('"ip", ts, "rebind-receive-acl", ts, word',
                                lambda x: {'name': x[0], 'format': 'ios_brocade',
                                           'receive_acl': True}),

    S('icomment'):            ('"!", ts?, icomment_body', lambda x: x),
    'icomment_body':            ('-"\n"*', Comment),
    S('ios_remark_line'):   ('("access-list", ts, digits_s, ts)?, "remark", ts, remark_body', lambda x: x),
    'remark_body':            ('-"\n"*', Remark),

    '>ios_line<':            ('ts?, (ios_acl_line / ios_ext_line / "end")?, '
                             'ts?, icomment?'),
    S('ios_acl'):            ('(ios_line, "\n")*, ios_line', handle_ios_acl),
})


#
# JunOS parsing
#


class QuotedString(str):
    def __str__(self):
        return '"' + self + '"'

def juniper_multiline_comments():
    """
    Return appropriate multi-line comment grammar for Juniper ACLs.

    This depends on ``settings.ALLOW_JUNIPER_MULTLIINE_COMMENTS``.
    """
    single = '-("*/" / "\n")*' # single-line comments only
    multi = '-"*/"*' # syntactically correct multi-line support
    if settings.ALLOW_JUNIPER_MULTILINE_COMMENTS:
        return multi
    return single

rules.update({
    'jword':                    'double_quoted / word',
    'double_quoted':            ('"\\"", -[\\"]+, "\\""',
                                 lambda x: QuotedString(x[1:-1])),

    #'>jws<':                    '(ws / jcomment)+',
    #S('jcomment'):              ('"/*", ws?, jcomment_body, ws?, "*/"',
    #                            lambda x: Comment(x[0])),
    #'jcomment_body':            '-(ws?, "*/")*',

    '>jws<':                    '(ws / jcomment)+',
    S('jcomment'):              ('jslashbang_comment',
                                 lambda x: Comment(x[0])),
    '<comment_start>':          '"/*"',
    '<comment_stop>':           '"*/"',
    '>jslashbang_comment<':     'comment_start, jcomment_body, !%s, comment_stop' % errs['comm_stop'],

    'jcomment_body':            juniper_multiline_comments(),

    # Errors on missing ';', ignores multiple ;; and normalizes to one.
    '<jsemi>':                  'jws?, [;]+!%s' % errs['semicolon'],

    'fragment_flag':            literals(fragment_flag_names),
    'ip_option':                "digits / " + literals(ip_option_names),
    'tcp_flag':                 literals(tcp_flag_names),
})

junos_match_types = []

def braced_list(arg):
    '''Returned braced output.  Will alert if comment is malformed.'''
    #return '("{", jws?, (%s, jws?)*, "}")' % arg
    return '("{", jws?, (%s, jws?)*, "}"!%s)' % (arg, errs['comm_start'])

def keyword_match(keyword, arg=None):
    for k in keyword, keyword+'-except':
        prod = 'junos_' + k.replace('-', '_')
        junos_match_types.append(prod)
        if arg is None:
            rules[prod] = ('"%s", jsemi' % k, {k: True})
        else:
            tokens = '"%s", jws, ' % k
            if k in address_matches:
                tokens += braced_list(arg + ', jsemi')
            else:
                tokens += arg + ', jsemi'
            rules[S(prod)] = (tokens, lambda x, k=k: {k: x})

keyword_match('address', 'cidr / ipaddr')
keyword_match('destination-address', 'cidr / ipaddr')
keyword_match('destination-prefix-list', 'jword')
keyword_match('first-fragment')
keyword_match('fragment-flags', 'fragment_flag')
keyword_match('ip-options', 'ip_option')
keyword_match('is-fragment')
keyword_match('prefix-list', 'jword')
keyword_match('source-address', 'cidr / ipaddr')
keyword_match('source-prefix-list', 'jword')
keyword_match('tcp-established')
keyword_match('tcp-flags', 'tcp_flag')
keyword_match('tcp-initial')

def range_match(key, arg):
    rules[S(arg+'_range')] = ('%s, "-", %s' % (arg, arg), tuple)
    match = '%s_range / %s' % (arg, arg)
    keyword_match(key, '%s / ("[", jws?, (%s, jws?)*, "]")' % (match, match))

range_match('ah-spi', 'alphanums')
range_match('destination-mac-address', 'macaddr')
range_match('destination-port', 'port')
range_match('dscp', 'dscp')
range_match('ether-type', 'alphanums')
range_match('esp-spi', 'alphanums')
range_match('forwarding-class', 'jword')
range_match('fragment-offset', 'port')
range_match('icmp-code', 'icmp_code')
range_match('icmp-type', 'icmp_type')
range_match('interface-group', 'digits')
range_match('packet-length', 'digits')
range_match('port', 'port')
range_match('precedence', 'jword')
range_match('protocol', 'protocol')
range_match('source-mac-address', 'macaddr')
range_match('source-port', 'port')
range_match('vlan-ether-type', 'alphanums')

def handle_junos_acl(x):
    """
    Parse JUNOS ACL and return an ACL object populated with Term and Policer
    objects.

    It's expected that x is a 2-tuple of (name, terms) returned from the
    parser.

    Don't forget to wrap your token in S()!
    """
    a = ACL(name=x[0], format='junos')
    for elt in x[1:]:
        if isinstance(elt, Term):
            a.terms.append(elt)
        elif isinstance(elt, Policer):
            #a.policers[elt.name] = elt
            a.policers.append(elt)
        else:
            raise RuntimeError('bad object: %s' % repr(elt))
    return a

def handle_junos_family_acl(x):
    """
    Parses a JUNOS acl that contains family information and sets the family
    attribute for the ACL object.

    It's expected that x is a 2-tuple of (family, aclobj) returned from the
    parser.

    Don't forget to wrap your token in S()!
    """
    family, aclobj = x
    setattr(aclobj, 'family', family)
    return aclobj

def handle_junos_policers(x):
    """Parse JUNOS policers and return a PolicerGroup object"""
    p = PolicerGroup(format='junos')
    for elt in x:
        if isinstance(elt, Policer):
            p.policers.append(elt)
        else:
            raise RuntimeError('bad object: %s in policer' % repr(elt))
    return p

def handle_junos_term(d):
    """Parse a JUNOS term and return a Term object"""
    if 'modifiers' in d:
        d['modifiers'] = Modifiers(d['modifiers'])
    return Term(**d)


# Note there cannot be jws (including comments) before or after the "filter"
# section of the config.  It's wrong to do this anyway, since if you load
# that config onto the router, the comments will not remain in place on
# the next load of a similar config (e.g., another ACL).  I had a workaround
# for this but it made the parser substantially slower.
rules.update({
    S('junos_raw_acl'):         ('jws?, "filter", jws, jword, jws?, ' + \
                                    braced_list('junos_term / junos_policer'),
                                    handle_junos_acl),
    'junos_replace_acl':        ('jws?, "firewall", jws?, "{", jws?, "replace:", jws?, (junos_raw_acl, jws?)*, "}"'),
    S('junos_replace_family_acl'): ('jws?, "firewall", jws?, "{", jws?, junos_filter_family, jws?, "{", jws?, "replace:", jws?, (junos_raw_acl, jws?)*, "}", jws?, "}"',
                                 handle_junos_family_acl),
    S('junos_replace_policers'):('"firewall", jws?, "{", jws?, "replace:", jws?, (junos_policer, jws?)*, "}"',
                                    handle_junos_policers),
    'junos_filter_family':      ('"family", ws, junos_family_type'),
    'junos_family_type':        ('"inet" / "inet6" / "ethernet-switching"'),
    'opaque_braced_group':      ('"{", jws?, (jword / "[" / "]" / ";" / '
                                    'opaque_braced_group / jws)*, "}"',
                                    lambda x: x),
    S('junos_term'):            ('maybe_inactive, "term", jws, junos_term_name, '
                                    'jws?, ' + braced_list('junos_from / junos_then'),
                                    lambda x: handle_junos_term(dict_sum(x))),
    S('junos_term_name'):       ('jword', lambda x: {'name': x[0]}),
    'maybe_inactive':           ('("inactive:", jws)?',
                                    lambda x: {'inactive': len(x) > 0}),
    S('junos_from'):            ('"from", jws?, ' + braced_list('junos_match'),
                                    lambda x: {'match': Matches(dict_sum(x))}),
    S('junos_then'):            ('junos_basic_then / junos_braced_then', dict_sum),
    S('junos_braced_then'):     ('"then", jws?, ' +
                                    braced_list('junos_action/junos_modifier, jsemi'),
                                    dict_sum),
    S('junos_basic_then'):      ('"then", jws?, junos_action, jsemi', dict_sum),
    S('junos_policer'):         ('"policer", jws, junos_term_name, jws?, ' +
                                    braced_list('junos_exceeding / junos_policer_then'),
                                    lambda x: Policer(x[0]['name'], x[1:])),
    S('junos_policer_then'):    ('"then", jws?, ' +
                                    braced_list('junos_policer_action, jsemi')),
    S('junos_policer_action'):  ('junos_discard / junos_fwd_class / '\
                                    '("loss-priority", jws, jword)',
                                    lambda x: {'action':x}),
    'junos_discard':            ('"discard"'),
    'junos_loss_pri':           ('"loss-priority", jws, jword',
                                    lambda x: {'loss-priority':x[0]}),
    'junos_fwd_class':          ('"forwarding-class", jws, jword',
                                    lambda x: {'forwarding-class':x[0]}),
    'junos_filter_specific':    ('"filter-specific"'),
    S('junos_exceeding'):       ('"if-exceeding", jws?, ' +
                                    braced_list('junos_bw_limit/junos_bw_perc/junos_burst_limit'),
                                    lambda x: {'if-exceeding':x}),
    S('junos_bw_limit'):        ('"bandwidth-limit", jws, word, jsemi',
                                    lambda x: ('bandwidth-limit',x[0])),
    S('junos_bw_perc'):         ('"bandwidth-percent", jws, alphanums, jsemi',
                                    lambda x: ('bandwidth-percent',x[0])),
    S('junos_burst_limit'):     ('"burst-size-limit", jws, alphanums, jsemi',
                                    lambda x: ('burst-size-limit',x[0])),
    S('junos_match'):           (' / '.join(junos_match_types), dict_sum),

    S('junos_action'):          ('junos_one_action / junos_reject_action /'
                                    'junos_reject_action / junos_ri_action',
                                    lambda x: {'action': x[0]}),
    'junos_one_action':         ('"accept" / "discard" / "reject" / '
                                    '("next", jws, "term")'),
    'junos_reject_action':      ('"reject", jws, ' + literals(icmp_reject_codes),
                                    lambda x: ('reject', x)),
    S('junos_ri_action'):       ('"routing-instance", jws, jword',
                                    lambda x: ('routing-instance', x[0])),
    S('junos_modifier'):        ('junos_one_modifier / junos_arg_modifier',
                                    lambda x: {'modifiers': x}),
    'junos_one_modifier':       ('"log" / "sample" / "syslog" / "port-mirror"',
                                    lambda x: (x, True)),
    S('junos_arg_modifier'):    'junos_arg_modifier_kw, jws, jword',
    'junos_arg_modifier_kw':    ('"count" / "forwarding-class" / "ipsec-sa" /'
                                    '"loss-priority" / "policer"'),
})

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
