# -*- coding: utf-8 -*-

"""
Parses and manipulates firewall policy for Juniper SRX firewall devices.
Broken apart from acl.parser because the approaches are vastly different from each
other.

CURRENT STATUS:
 * Work in progress
 * (see /shared/ for more notes)
"""

__author__ = 'Jathan McCollum, Mark Thomas, Joseph Malone'
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
__all__ = ('JuniperSRX', 'SRXPolicy', 'SRXZone')

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
        self.zones          = []
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
            S('root'):     'jws?, security', #/ zones'),
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
           
            S('security'):                  '"security", jws?,' + braced_list('policies / zones'), #
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
            #Zones !!
            S('zones'):                     '"zones", jws?,' + braced_list('security_zone_section+'),
            S('security_zone_section'):     '"security-zone", jws?, security_zone, jws?,' + braced_list('address_book+ / host_inbound_traffic / interfaces'),
            'security_zone':                'jword',
            S('address_book'):              '"address-book", jws?,' + braced_list('address_book_address+ / address_set+'),
            'address_book_address':         '"address", jws?, ipv4/address_obj, jws?, jword, ";"', #fix jword
            S('address_set'):               '"address-set", jws?, address_obj, jws?,' + braced_list('address_set_address+'),
            'address_set_address':          '"address", jws?, ipv4, ";"',
            S('host_inbound_traffic'):      '"host-inbound-traffic", jws?,' + braced_list('system_services+'),
            S('system_services'):           '"system-services", jws?,' + braced_list('system_services_item+'),
            'system_services_item':         'jword, ";"',
            S('interfaces'):                '"interfaces", jws?,' + braced_list('interfaces_item+'),
            'interfaces_item':              'jword, ";"',
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
        parser = ACLParser(self.grammar)
        try:
            string = data.read()
        except AttributeError:
            string = data

        success, children, nextchar = parser.parse(string)

        if success and nextchar == len(string):
            assert len(children) == 1
            return children[0]
        else:
            line = string[:nextchar].count('\n') + 1
            column = len(string[string[nextchar].rfind('\n'):nextchar]) + 2
            print "Error at: ", string[nextchar:]
            raise exceptions.ParseError('Could not match syntax. Please report as a bug.', line, column)

    def output(self):
        pass

def rip_list(parsed_list=[]):
    """
    Take in a list that has been parsed and rip it apart into its appropriate objects
    Return a JuniperSRX object
    """
    data_list = parsed_list[:]
    from_to_zones = data_list[0]

    jSRX = JuniperSRX()
    
    for zone in from_to_zones:
        from_zone = zone[0]
        zone.remove(from_zone)
        to_zone = zone[0]
        zone.remove(to_zone)
        for policy_list in zone:
            policy = SRXPolicy(policy_list, from_zone, to_zone)
            jSRX.policies.append(policy)

    zones = data_list[1]   
    for zone_list in zones:
       zone = SRXZone(zone_list) 
       jSRX.zones.append(zone)
    return jSRX

class SRXPolicy(JuniperSRX):
    """
    Container for individual policy definitions. This is strictly based on the grammar for SRX.
    All the positions in the lists are hardcorded. If the grammar gets changed, change this, too.
    """
    #TODO: Design this better. It works, but may break in many cases
    def __init__(self, parsed_list = [], from_zone="", to_zone=""):
        self.store_list = parsed_list[:]
        self.from_zone = from_zone
        self.to_zone = to_zone
        self.name = self.store_list[0]
        self.match_source_address = self.store_list[1][0]
        self.match_destination_address = self.store_list[1][1]
        if len(self.store_list[2][0]) > 2:
            self.match_application = self.store_list[1][2]
        self.then_action = self.store_list[2][0]
        if len(self.store_list[2][0]) > 1:
            self.then_log = self.store_list[2][1]

class SRXZone(JuniperSRX):
    """
    Container for individual zone definitions. This is strictly based on the grammar for SRX.
    All the positions in the lists are hardcorded. If the grammar gets changed, change this, too.
    """
    #TODO: Design this better. It works, but may break in many cases
    def __init__(self, parsed_list = []):
        self.store_list = parsed_list[:]
        self.name = self.store_list[0]
        #TODO: create little address_book objects to hold pairs for the most part
        self.address_book = self.store_list[1]    
        if len(self.store_list) > 2:
            self.host_inbound_traffic = self.store_list[2]
        if len(self.store_list) > 3:
            self.interfaces = self.store_list[3]           
