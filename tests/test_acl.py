#!/usr/bin/python
# -*- coding: utf-8 -*-

__author__ = 'Jathan McCollum, Michael Shields'
__maintainer__ = 'Jathan McCollum'
__copyright__ = 'Copyright 2005-2011 AOL Inc.; 2013 Salesforce.com'
__version__ = '2.0'

from StringIO import StringIO
import unittest
from trigger import acl, exceptions

EXAMPLES_FILE = 'tests/data/junos-examples.txt'

# Some representative match clauses:
ios_matches = ('tcp 192.0.2.0 0.0.0.255 any gt 65530',                # 1
               'udp any host 192.0.2.99 eq 80',                        # 2
               '16 any host 192.0.2.99',                        # 3
               'tcp any host 192.0.2.99 range 1 4 established',        # 4
               'icmp any any 13 37',                                # 5
               'icmp any any unreachable',                        # 6
               'icmp any any echo-reply',                        # 7
               'tcp 192.0.2.96 0.0.0.31 any eq 80',                # 8
               'ip any any')


class CheckRangeList(unittest.TestCase):
    """Test functionality of RangeList object"""
    def testDegenerateRange(self):
        """Make sure that the range x-x is the same as x."""
        r = acl.RangeList([(1024, 1024)])
        self.assertEqual(r, [1024])

    def testDuplicateProtocol(self):
        """Test duplicate protocols."""
        # Regression: These weren't suppresed because they are unique
        # objects, and so a Set can contain more than one of them.
        r = acl.RangeList([acl.Protocol(6), acl.Protocol(6)])
        self.assertEqual(r, [acl.Protocol(6)])

    def testAdjacentRanges(self):
        """See if adjacent ranges are coalesced into one."""
        r = acl.RangeList([(100, 199), (200, 299)])
        self.assertEqual(r, [(100, 299)])

    def testOverlappingRanges(self):
        """See if overlapping ranges are coalesced into one."""
        r = acl.RangeList([(100, 250), (200, 299)])
        self.assertEqual(r, [(100, 299)])

    def testOverlappingRangeAndInteger(self):
        """See if a single value that's also part of a range is elided."""
        r = acl.RangeList([(100, 199), 150])
        self.assertEqual(r, [(100, 199)])

    def testMultipleConstants(self):
        """See if several discrete values are collapsed correctly."""
        r = acl.RangeList([5, 5, 5, 8, 9, 10])
        self.assertEqual(r, [5, (8, 10)])

    def testNonIncrementable(self):
        """Make sure non-incrementable values can be stored."""
        r = acl.RangeList(['y', 'x'])
        self.assertEqual(r, ['x', 'y'])

    def testRangeListContains(self):
        """Check RangeList behavior as a container type."""
        r = acl.RangeList([1, (3, 6)])
        self.assertTrue(1 in r)
        self.assertTrue(5 in r)
        self.assertTrue(0 not in r)
        r = acl.RangeList([acl.TIP('10/8'), acl.TIP('172.16/12')])
        self.assertTrue(acl.TIP('10.1.1.1') in r)
        self.assertTrue(acl.TIP('192.168.1.1') not in r)

class CheckACLNames(unittest.TestCase):
    """Test ACL naming validation"""
    def testOkNames(self):
        """Test names that are valid in at least one vendor's ACLs"""
        names = ('101', '131mj', 'STR-MDC-ATM', 'with space', '3.14', None)
        for name in names:
            a = acl.ACL(name=name)

    def testBadNames(self):
        """Test names that are valid in no vendor's ACLs"""
        for name in ('', 'x'*25):
            try:
                a = acl.ACL(name=name)
            except exceptions.ACLNameError:
                pass
            else:
                self.fail('expected ACLNameError on "' + name + '"')

class CheckACLTerms(unittest.TestCase):
    """Test insertion of Term objects into an ACL object"""
    def testEmptyAnonymousTerms(self):
        """Test inserting multiple anonymous empty terms"""
        a = acl.ACL()
        for i in range(5):
            a.terms.append(acl.Term())
            self.assertEqual(a.terms[i].name, None)
        self.assertEqual(len(a.terms), 5)

    def testEmptyNamedTerms(self):
        """Test inserting multiple anonymous named terms"""
        a = acl.ACL()
        for i in range(5):
            name = 'term' + str(i)
            a.terms.append(acl.Term(name))
            self.assertEqual(a.terms[i].name, name)
        self.assertEqual(len(a.terms), 5)

class CheckTerms(unittest.TestCase):
    """Test validity and functionality of Term objects"""
    def testOkNames(self):
        """Test valid JunOS term names"""
        for name in ('101', 'T1337', 'sr12345', '3.1415926'):
            t = acl.Term(name=name)

    def testBadNames(self):
        """Test invalid JunOS term names"""
        for name in ('', 'x'*300):
            try:
                t = acl.Term(name=name)
            except exceptions.BadTermName:
                pass
            else:
                self.fail('expected BadTermNameon "' + name + '"')

    def testOkActions(self):
        """Test valid filter actions"""
        for action in (('next', 'term'), ('routing-instance', 'blah'),
                       ('reject', 'tcp-reset'), 'accept', 'discard'):
            t = acl.Term(action=action)
            if isinstance(action, tuple):
                self.assertEqual(t.action, action)
            else:
                self.assertEqual(t.action, (action,))
                t = acl.Term(action=(action,))
                self.assertEqual(t.action, (action,))
        for action in ('deny', 'reject',
                       ('reject', 'administratively-prohibited')):
            t = acl.Term(action=action)
            self.assertEqual(t.action, ('reject',))
        t = acl.Term(action='permit')
        self.assertEqual(t.action, ('accept',))

    def testBadActions(self):
        """Test invalid filter actions"""
        t = acl.Term()
        for action in ('blah', '', ('reject', 'because-I-said-so'),
                       ('routing-instance', 'x'*300), 'sample'):
            try:
                t = acl.Term(action=action)
            except exceptions.ActionError:
                pass
            else:
                self.fail('expected ActionError on "%s"' % str(action))

    def testOkModifiers(self):
        """Test valid filter action modifiers"""
        t = acl.Term(action='discard')
        for action in (('count', 'abc'), ('forwarding-class', 'abc'),
                       ('ipsec-sa', 'abc'), 'log', ('loss-priority', 'low'),
                       ('policer', 'abc'), 'sample', 'syslog'):
            t.set_action_or_modifier(action)
            if isinstance(action, tuple):
                self.assertEqual(t.modifiers[action[0]], action[1])
            else:
                self.assertEqual(t.modifiers[action], None)
                t.set_action_or_modifier((action,))
                self.assertEqual(t.modifiers[action], None)
        # Make sure none of these modified the primary action.
        self.assertEqual(t.action, ('discard',))

    def testBadModifiers(self):
        """Test invalid filter action modifiers"""
        for action in (('count', ''), ('count',), 'count', ('count', 'a-b-c'),
                       ('loss-priority', '17'), ('sample', 'abc')):
            try:
                t = acl.Term(action=action)
            except exceptions.ActionError:
                pass
            else:
                self.fail('expected ActionError on "%s"' % str(action))

    def testOkMatches(self):
        """Test valid match conditions"""
        t = acl.Term()
        t.match['destination-port'] = [25]
        self.assertEqual(t.match['destination-port'], [25])
        t.match['destination-port'] = range(100, 200)
        self.assertEqual(t.match['destination-port'], [(100, 199)])
        t.match['source-port'] = ['tftp']
        self.assertEqual(t.match['source-port'], [69])
        t.match['protocol'] = ['ospf', 6, 17]
        self.assertEqual(t.match['protocol'], [6, 17, 89])
        t.match['fragment-offset'] = [1337]
        self.assertEqual(t.match['fragment-offset'], [1337])
        t.match['icmp-type'] = ['unreachable']
        self.assertEqual(t.match['icmp-type'], [3])
        t.match['destination-address'] = ['192.0.2.0/24']
        self.assertEqual(str(t.match['destination-address'][0]), '192.0.2.0/24')
        t.match['source-prefix-list'] = ['blah']
        self.assertEqual(t.match['source-prefix-list'], ['blah'])

    def testBadMatches(self):
        """Test invalid match conditions"""
        t = acl.Term()
        # Valid match type with invalid arg.
        try:
            t.match['fragment-offset'] = [65536]
        except exceptions.BadMatchArgRange:
            pass
        else:
            self.fail('expected MatchError')
        # Valid match type with non-list argument.
        try:
            t.match['fragment-offset'] = 0
        except TypeError:
            pass
        else:
            self.fail('expected MatchError')
        # Valid match type with null arg.
        try:
            t.match['protocol'] = None
        except exceptions.MatchError:
            pass
        else:
            self.fail('expected MatchError')
        # Invalid match type.
        try:
            t.match['boogaloo'] = 1337
        except exceptions.MatchError:
            pass
        else:
            self.fail('expected MatchError')

class CheckProtocolClass(unittest.TestCase):
    """Test functionality of Protocol object"""
    def testKnownProto(self):
        """Test magic stringification of a known numeric protocol."""
        p = acl.Protocol(6)
        self.assertEqual(str(p), 'tcp')
        self.assertEqual(p, 'tcp')
        self.assertEqual(p, 6)

    def testNamedProto(self):
        """Test magic stringification of a named protocol."""
        p = acl.Protocol('tcp')
        self.assertEqual(str(p), 'tcp')
        self.assertEqual(p, 'tcp')
        self.assertEqual(p, 6)

    def testUnknownProto(self):
        """Test magic stringification of a numeric protocol."""
        p = acl.Protocol('99')
        self.assertEqual(str(p), '99')
        self.assertEqual(p, '99')
        self.assertEqual(p, 99)


class CheckOutput(unittest.TestCase):
    """Test .output() methods for various ACL vendors"""
    def setUp(self):
        super(CheckOutput, self).setUp()
        self.a = acl.ACL()
        self.t1 = acl.Term(name='p99')
        self.t1.match['protocol'] = [99]
        self.t1.action = 'accept'
        self.a.terms.append(self.t1)
        self.t2 = acl.Term(name='windows')
        self.t2.match['protocol'] = ['tcp']
        self.t2.match['source-address'] = ['192.0.2.0/24']
        self.t2.match['destination-port'] = range(135, 139) + [445]
        self.t2.action = 'reject'
        self.t2.modifiers['syslog'] = True
        self.a.terms.append(self.t2)

    def testJunOS(self):
        """Test conversion of ACLs and terms to JunOS format"""
        self.a.name = '100j'
        self.t1.modifiers['count'] = 'p99'
        output = """\
filter 100j {
    term p99 {
        from {
            protocol 99;
        }
        then {
            accept;
            count p99;
        }
    }
    term windows {
        from {
            source-address {
                192.0.2.0/24;
            }
            protocol tcp;
            destination-port [ 135-138 445 ];
        }
        then {
            reject;
            syslog;
        }
    }
}"""
        self.assertEqual(self.a.output_junos(), output.split('\n'))

    def testIOS(self):
        """Test conversion of ACLs and terms to IOS classic format"""
        self.a.name = 100
        try:
            del self.t1.modifiers['count']
        except KeyError:
            pass
        output = """\
access-list 100 permit 99 any any
access-list 100 deny tcp 192.0.2.0 0.0.0.255 any range 135 138 log
access-list 100 deny tcp 192.0.2.0 0.0.0.255 any eq 445 log"""
        self.assertEqual(self.a.output_ios(), output.split('\n'))

    def testIOSExtended(self):
        """Test conversion of ACLs and terms to IOS extended format"""
        self.a.name = 'BLAHBLAH'
        try:
            del self.t1.modifiers['count']
        except KeyError:
            pass
        output = """\
ip access-list extended BLAHBLAH
 permit 99 any any
 deny tcp 192.0.2.0 0.0.0.255 any range 135 138 log
 deny tcp 192.0.2.0 0.0.0.255 any eq 445 log"""
        self.assertEqual(self.a.output_ios_named(), output.split('\n'))

    def testIOSXR(self):
        """Test conversion of ACLs and terms to IOS XR format"""
        self.a.name = 'BLAHBLAH'
        try:
            del self.t1.modifiers['count']
        except KeyError:
            pass
        self.t1.name = self.t2.name = None
        output = """\
ipv4 access-list BLAHBLAH
 10 permit 99 any any
 20 deny tcp 192.0.2.0 0.0.0.255 any range 135 138 log
 30 deny tcp 192.0.2.0 0.0.0.255 any eq 445 log"""
        self.assertEqual(self.a.output_iosxr(), output.split('\n'))

    def testMissingTermName(self):
        """Test conversion of anonymous terms to JunOS format"""
        self.assertRaises(exceptions.MissingTermName, acl.Term().output_junos)

    def testMissingACLName(self):
        """Test conversion of anonymous ACLs to JunOS format"""
        self.assertRaises(exceptions.MissingACLName, acl.ACL().output_junos)

    def testBadACLNames(self):
        """Test conversion of ACLs with vendor-invalid names"""
        a = acl.ACL()
        for bad_name in ('blah', '500', '1', '131dj'):
            a.name = bad_name
            self.assertRaises(exceptions.BadACLName, a.output_ios)

class CheckIOSParseAndOutput(unittest.TestCase):
    """Test parsing of IOS ACLs"""
    def testIOSACL(self):
        """Test parsing of IOS numbered ACLs."""
        text = '\n'.join(['access-list 100 permit ' + x for x in ios_matches])
        self.assertEqual('\n'.join(acl.parse(text).output_ios()), text)
        # Non-canonical forms:
        x = 'access-list 100 permit icmp any any log echo'
        y = 'access-list 100 permit icmp any any echo log'
        a = acl.parse(x)
        self.assertEqual(a.output_ios(), [y])
        self.assertEqual(a.format, 'ios')

    def testIOSNamedACL(self):
        """Test parsing of IOS named ACLs."""
        x = 'ip access-list extended foo\n'
        x += '\n'.join([' permit ' + x for x in ios_matches])
        a = acl.parse(x)
        self.assertEqual(a.output_ios_named(), x.split('\n'))
        self.assertEqual(a.format, 'ios_named')

    def testIOSNamedACLRemarks(self):
        """Test parsing of 'remark' lines in IOS named ACLs."""
        x = '''\
ip access-list extended foo
 permit nos any any
 remark Need more NOS!
 permit nos any any'''
        self.assertEqual(acl.parse(x).output_ios_named(), x.split('\n'))

    def testIOSACLDecoration(self):
        """Test IOS ACLs with comments, blank lines, and "end"."""
        x = '\n! comment\n\naccess-list 100 permit udp any any log ! ok\nend\n'
        y = ['! ok', '! comment', 'access-list 100 permit udp any any log']
        a = acl.parse(x)
        self.assertEqual(a.output_ios(), y)

    def testIOSACLNegation(self):
        """Test handling of "no access-list" command."""
        x = ['access-list 100 permit udp any any',
             'no access-list 100',
             'access-list 100 permit tcp any any']
        self.assertEqual(acl.parse('\n'.join(x)).output_ios(), x[-1:])

    def testIOSBadACL(self):
        """Test handling of a bad ACL."""
        text = 'access-list 145 permit tcp any any;\naccess-list 145 deny ip any any'
        self.assertRaises(exceptions.ParseError, lambda: acl.parse(text))

    def testIOSNonCanonical(self):
        """Test parsing of IOS match terms in non-output formats."""
        x = 'access-list 100 permit tcp any any eq ftp-data'
        y = 'access-list 100 permit tcp any any eq 20'
        self.assertEqual(acl.parse(x).output_ios(), [y])
        x = 'access-list 100 permit ip any 192.0.2.99 0.0.0.0'
        y = 'access-list 100 permit ip any host 192.0.2.99'
        self.assertEqual(acl.parse(x).output_ios(), [y])

    def testIOSLongComments(self):
        """Test long comments in IOS ACLs."""
        # Regression: naïve comment handling caused this to exceed the
        # maximum recursion depth.
        acl.parse('!'*200 + '\naccess-list 100 deny ip any any')

class CheckJunOSExamples(unittest.TestCase):
    """Test parsing of Junos ACLs"""
    def testJunOSExamples(self):
        """Test examples from JunOS documentation."""
        examples = file(EXAMPLES_FILE).read().expandtabs().split('\n\n')
        # Skip the last two because they use the unimplemented "except"
        # feature in address matches.
        for i in range(0, 14, 2):
            if examples[i+1].find('policer'):
                continue
            x = examples[i+1].split('\n')
            y = acl.parse(examples[i]).output_junos()
            self.assertEqual(x, y)
            self.assertEqual(y.format, 'junos')
            z = acl.parse('\n'.join(y)).output_junos()
            self.assertEqual(y, z)

class CheckMiscJunOS(unittest.TestCase):
    """Test misc. Junos-related ACL features"""
    def testFirewallReplace(self):
        """Test JunOS ACL with "firewall { replace:" around it."""
        acl.parse('''
firewall {
replace:
    filter blah {
        term foo { 
            then {
                accept;
            }
        }
    }
}''')

    def testTCPFlags(self):
        """Test tcp-established and is-fragment."""
        x = '''\
filter x {
    term y {
        from {
            is-fragment;
            tcp-established;
        }
        then {
            accept;
        }
    }
}'''
        self.assertEqual(x, '\n'.join(acl.parse(x).output_junos()))

    def testPacketLengthString(self):
        """Test packet-length as a string."""
        # Previous bug failed to parse this into an integer.
        t = acl.Term()
        t.match['packet-length'] = ['40']
        self.assertEqual(t.match['packet-length'], [40])

    def testInactiveTerm(self):
        """Test terms flagged as inactive."""
        x = '''\
filter 100 {
    term t1 {
        then {
            reject;
        }
    }
    inactive: term t2 {
        then {
            accept;
        }
    }
    term t3 {
        then {
            accept;
        }
    }
}'''
        y = acl.parse(x)
        self.assertEqual(y.output_junos(), x.split('\n'))
        self.assertRaises(exceptions.VendorSupportLacking, y.output_ios)

    def testInterfaceSpecific(self):
        """Test support of Juniper 'interface-specific statement"""
        x = '''filter x { interface-specific; term y { then accept; } }'''
        y = acl.parse(x)
        self.assertTrue(y.interface_specific)
        self.assertEqual(y.output_junos()[1], '    interface-specific;')

    def testShorthandIPv4(self):
        """Test incomplete IP blocks like "10/8" (vs. "10.0.0.0/8")."""
        x = '''filter x { term y { from { address { 10/8; } } } }'''
        y = acl.parse(x)
        self.assertEqual(y.terms[0].match['address'][0].strNormal(),
                         '10.0.0.0/8')

    def testModifierWithoutAction(self):
        """Test modifier without action."""
        x = '''filter x { term y { then { count z; } } }'''
        y = acl.parse(x)
        self.assertEqual(y.terms[0].action, ('accept',))

    def testNameTerms(self):
        """Test automatic naming of terms."""
        a = acl.ACL()
        a.terms.append(acl.Term())
        a.terms.append(acl.Term())
        a.terms.append(acl.Term(name='foo'))
        a.name_terms()
        self.assertNotEqual(a.terms[0].name, None)
        self.assertNotEqual(a.terms[0].name, a.terms[1].name)
        self.assertEqual(a.terms[2].name, 'foo')

    def testCommentStress(self):
        #'''Test pathological JunOS comments.'''
        '''Test pathological JunOS comments. We want this to error in order to pass.
        NO MULTI-LINE COMMENTS!!
        '''
        x = '''
filter 100 {
    /* one */  /* two */
    term/* */y {
        from /*{*/ /******/ {
            protocol tcp; /*
            */ destination-port 80/**/;
            /* tcp-established; */
        }
        /* /* /* */
    }
}'''
        self.assertRaises(exceptions.ParserSyntaxError, lambda: acl.parse(x))
        ###y = ['access-list 100 permit tcp any any eq 80']
        ###a = acl.parse(x)
        ###a.comments = a.terms[0].comments = []
        ###self.assertEqual(a.output_ios(), y)

    def testRanges(self):
        '''Test JunOS ICMP and protocol ranges (regression).'''
        x = '''
    filter 115j {
        term ICMP {
            from {
                protocol tcp-17;
                icmp-type [ echo-reply 10-11 ];
            }
            then {
                accept;
                count ICMP;
            }
        }
    }'''
        a = acl.parse(x)

    def testDoubleQuotes(self):
        '''Test JunOS double-quoted names (regression).'''
        x = '''\
filter test {
    term "awkward term name" {
        then {
            accept;
            count "awkward term name";
        }
    }
}'''
        a = acl.parse(x)
        self.assertEqual(a.terms[0].name, 'awkward term name')
        self.assertEqual('\n'.join(a.output_junos()), x)

    def testReplace(self):
        '''Test "firewall { replace:" addition.'''
        a = acl.ACL('test')
        self.assertEqual('\n'.join(a.output_junos(replace=True)), '''\
firewall {
replace:
    filter test {
    }
}''')

    def testNextTerm(self):
        '''Test "next term" action (regression).'''
        x = 'filter f { term t { then { next term; } } }'
        a = acl.parse(x)

    def testPolicer(self):
        '''test policer stuff.'''
        x = \
'''firewall {
replace:
    policer test {
        if-exceeding {
            bandwidth-limit 32000;
            burst-size-limit 32000;
        }
        then {
            discard;
        }
    }
    policer test2 {
        if-exceeding {
            bandwidth-limit 32000;
            burst-size-limit 32000;
        }
        then {
            discard;
        }
    }
}'''
        a = acl.parse(x)
        self.assertEqual(a.output(replace=True), x.split('\n'))
    
class CheckMiscIOS(unittest.TestCase):
    """Test misc. IOS-related ACL features"""
    def testICMPIOSNames(self):
        """Test stringification of ICMP types and codes into IOS format."""
        x = 'access-list 100 permit icmp 172.16.0.0 0.15.255.255 any 8'
        y = 'access-list 100 permit icmp 172.16.0.0 0.15.255.255 any echo'
        self.assertEqual(acl.parse(x).output_ios(), [y])
        self.assertEqual(acl.parse(y).output_ios(), [y])

    def testICMPRanges(self):
        """Test ICMP range conversions into IOS format."""
        types = [1, 111, 112, 113]
        t = acl.Term()
        t.match['protocol'] = ['icmp']
        t.match['icmp-type'] = types
        self.assertEqual(t.output_ios(),
                         map(lambda x: 'permit icmp any any %d' % x, types))

    def testCounterSuppression(self):
       """Test suppression of counters in IOS (since they are implicit)."""
       t = acl.Term()
       t.modifiers['count'] = 'xyz'
       t.output_ios()  # should not raise VendorSupportLacking

class CheckParseFile(unittest.TestCase):
    """Test ACL parsing from a file"""
    def testParseFile(self):
        """Make sure we can apply trigger.acl.parse() to file objects."""
        a = acl.parse(StringIO('access-list 100 deny ip any any'))
        self.assertEqual(a.name, '100')

class CheckTriggerIP(unittest.TestCase):
    """Test functionality of Trigger IP (TIP) objects."""
    def setUp(self):
        self.test_net = acl.TIP('1.2.3.0/24')

    def testRegular(self):
        """Test a normal IP object"""
        test = '1.2.3.4'
        obj = acl.TIP(test)
        self.assertEqual(str(obj), test)
        self.assertEqual(obj.negated, False)
        self.assertEqual(obj.inactive, False)
        self.assertTrue(obj in self.test_net)

    def testNegated(self):
        """Test a negated IP object"""
        test = '1.2.3.4/32 except'
        obj = acl.TIP(test)
        self.assertEqual(str(obj), test)
        self.assertEqual(obj.negated, True)
        self.assertEqual(obj.inactive, False)
        self.assertFalse(obj in self.test_net)

    def testInactive(self):
        """Test an inactive IP object"""
        test = 'inactive: 1.2.3.4/32'
        obj = acl.TIP(test)
        self.assertEqual(str(obj), test)
        self.assertEqual(obj.negated, False)
        self.assertEqual(obj.inactive, True)
        # Until we fix inactive testing, this is legit
        self.assertTrue(obj in self.test_net)

    def testInactive(self):
        """Test an inactive IP object"""
        test = 'inactive: 1.2.3.4/32 except'
        obj = acl.TIP(test)
        self.assertEqual(str(obj), test)
        self.assertEqual(obj.negated, True)
        self.assertEqual(obj.inactive, True)
        # Inactive and negated is always negated
        self.assertFalse(obj in self.test_net)

if __name__ == "__main__":
    unittest.main()
