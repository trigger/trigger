# -*- coding: utf-8 -*-

"""
Parses and manipulates firewall policy for Juniper SRX firewall devices.
Broken apart from acl.parser because the approaches are vastly different from each
other.

CURRENT STATUS:
 * Need to remove, refactor more of the existing NetScreen functions.
 * Need to complete restructuring of classes (associate address books with their
   parent policies, maybe other tasks)
 * (see /shared/ for more notes)
"""

__author__ = 'Jathan McCollum, Mark Thomas'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2007-2012, AOL Inc.'
__version__ = '1.2.2'

import IPy
from trigger.acl.parser import (Protocol, check_range, literals, TIP,
        do_protocol_lookup, make_nondefault_processor,
        ACLParser, ACLProcessor, default_processor, S, errs, juniper_multiline_comments,
        settings, fragment_flag_names, ip_option_names, tcp_flag_names, rules)
from trigger.acl.tools import create_trigger_term
from trigger import exceptions


# TODO (jathan): Implement __all__
__all__ = ()

def braced_list(arg):
    '''Returned braced output.  Will alert if comment is malformed.'''
    #return '("{", jws?, (%s, jws?)*, "}")' % arg
    return '("{", jws?, (%s, jws?)*, "}"!%s)' % (arg, errs['comm_start'])


# Classes
class JuniperSRX(object):
    """
    Parses and generates Juniper SRX firewall policy.
    """
    def __init__(self):
        #self.applications   = SRXApplications()
        self.interfaces     = []
        self.address_groups = []
        self.service_groups = []
        self.policies       = []
        self.grammar        = []

        rules = {
            #
            # normal shiznitches.
            #
            'digits':    '[0-9]+',
            '<ts>':      '[ \\t]+',
            '<ws>':      '[ \\t\\n]+',
            '<EOL>':     "('\r'?,'\n')/EOF",
            'alphanums': '[a-zA-z0-9]+',
            'word':      '[a-zA-Z0-9_:./-]+',
            'anychar':   "[ a-zA-Z0-9.$:()&,/'_-]",
            'nonspace':  "[a-zA-Z0-9.$:()&,/'_-]+",
            'ipv4':      ('digits, (".", digits)*', TIP),
            'cidr':      ('ipv4, "/", digits', TIP),
            'macaddr':   '[0-9a-fA-F:]+',
            'protocol':  (literals(Protocol.name2num) + ' / digits',
                            do_protocol_lookup),
            'tcp':       ('"tcp" / "6"', Protocol('tcp')),
            'udp':       ('"udp" / "17"', Protocol('udp')),
            'icmp':      ('"icmp" / "1"', Protocol('icmp')),
            #root is used as "production" for the parser. This is the beginning of the parsing tree
            S('root'):     'jws?, "security", jws?, "{", ws, policies, ws, "}"',
            #
            # Junos general grammar stuff (copied from /trigger/acl/junos.py)
            #
            'jword':                    'double_quoted / word',
            'double_quoted':            ('"\\"", -[\\"]+, "\\""',
                                         lambda x: QuotedString(x[1:-1])),
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
            #
            # Juniper SRX-specific grammar (some inspiration from /trigger/acl/junos.py)
            # TODO: come up with this grammar
            
            #jws? DEMANDS A space!!!
#             S('policies'):                  '"policies", jws?, "{", jws?, from_to_zone_section+, jws?, "}"',

            S('policies'):                  '"policies", jws?,' + braced_list('from_to_zone_section+'),
            S('from_to_zone_section'):      '"from-zone", jws?, from_zone, jws?, "to-zone", jws?, to_zone, jws?,' + braced_list('policy+'),
            'from_zone':                    'jword',
            'to_zone':                      'jword',
            S('policy'):                    'jws?, "policy", jws?, alphanums, jws?,' + braced_list('match / then'),
            S('match'):                     '"match", jws?,' + braced_list('source_address / destination_address / application'),
            S('source_address'):            '"source-address", jws?, ipv4/address_obj, jws?, ";"',
            S('destination_address'):       '"destination-address", jws?, ipv4/address_obj, jws?, ";"',
            S('application'):               '"application", jws?, jword, jws?, ";"',
            'address_obj':                  'jword',
            S('then'):                      '"then", jws?, "{", jws?, action, jws?, ";", jws?, log*, jws?, "}"',
            'action':                       'jword',
            'log':                          '"log", jws?, "{", jws?, "session-init;", jws?, "session-close;", jws?, "}"',


         

#acl = parser.parse("filter 123 { term T1 { from { destination-address { 10.20.30.40/32; } protocol tcp; destination-port 80; } then { accept; } } }")



        }

        for production, rule, in rules.iteritems():
            if isinstance(rule, tuple):
                assert len(rule) == 2
                setattr(ACLProcessor, production, make_nondefault_processor(rule[1]))
                self.grammar.append('%s := %s' % (production, rule[0]))
            else:
                setattr(ACLProcessor, production, default_processor)
                self.grammar.append('%s := %s' % (production, rule))

        self.grammar = '\n'.join(self.grammar)

    #For multiline comments
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


    def parse(self, data):
        """Parse policy into list of NSPolicy objects."""
        #print self.grammar
        parser = ACLParser(self.grammar)
        try:
            string = data.read()
        except AttributeError:
            string = data

        success, children, nextchar = parser.parse(string)

        #print success
        #print children
        #print nextchar
        #print string
        #print data
        #print len(string)

        if success and nextchar == len(string):
            assert len(children) == 1
            print children
            return children[0]
        else:
            line = string[:nextchar].count('\n') + 1
            column = len(string[string[nextchar].rfind('\n'):nextchar]) + 2
            print "Error at: ", string[nextchar:]
            raise exceptions.ParseError('Could not match syntax. Please report as a bug.', line, column)

    def netmask2cidr(self, iptuple):
        """Converts dotted-quad netmask to cidr notation"""
        if len(iptuple) == 2:
            addr, mask = iptuple
            ipstr = addr.strNormal() + '/' + mask.strNormal()
            return TIP(ipstr)
        return TIP(iptuple[0].strNormal())


    def output(self):
        ret = []
        for ent in self.address_book.output():
            ret.append(ent)
        for ent in self.service_book.output():
            ret.append(ent)
        for ent in self.policies:
            for line in ent.output():
                ret.append(line)
        return ret

    def output_terms(self):
        ret = []
        for ent in self.policies:
            for term in ent.output_terms():
                ret.append(term)
        return ret
