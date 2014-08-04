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
                                ACLParser, ACLProcessor, default_processor, S)
from trigger.acl.tools import create_trigger_term
from trigger import exceptions


# TODO (jathan): Implement __all__
__all__ = ('NSRawPolicy', 'NSRawGroup', 'JuniperSRX', 'NSGroup',
           'NSServiceBook', 'NSAddressBook', 'NSAddress', 'NSService',
           'NSPolicy')

class QuotedString(str):
    def __str__(self):
        return '"' + self + '"'

# Classes
class JuniperSRX(object):
    """
    Parses and generates Juniper SRX firewall policy.
    """
    def __init__(self):
        self.applications   = SRXApplications()
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
            'root':      'ws?, netscreen, ws?',
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

    def braced_list(arg):
        '''Returned braced output.  Will alert if comment is malformed.'''
        #return '("{", jws?, (%s, jws?)*, "}")' % arg
        return '("{", jws?, (%s, jws?)*, "}"!%s)' % (arg, errs['comm_start'])

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

############################
# Policy/Service/Group stuff
############################
class NSRawGroup(object):
    """
    Container for group definitions.
    """
    def __init__(self, data):
        if data[0] == 'address' and len(data) == 3:
            data.append(None)
        if data[0] == 'service' and len(data) == 2:
            data.append(None)

        self.data = data
    def __iter__(self):
        return self.data.__iter__()
    def __len__(self):
        return self.data.__len__()

class NSGroup(NetScreen):
    """
    Container for address/service groups.
    """
    def __init__(self, name=None, group_type='address', zone=None):
        self.nodes = []
        self.name = name
        self.type = group_type
        self.zone = zone

    def append(self, item):
        return getattr(self, 'add_' + self.type)(item)

    def add_address(self, addr):
        assert self.type == 'address'
        if not isinstance(addr, NSAddress):
            raise "add_address requires NSAddress object"
        # make sure the entry hasn't already been added, and
        # that all the zones are in the same zone
        for i in self.nodes:
            if i.zone != addr.zone:
                raise "zone %s did not equal others in group" % addr.zone
            if i.name == addr.name:
                return
        self.nodes.append(addr)

    def add_service(self, svc):
        assert self.type == 'service'
        if not isinstance(svc, NSService):
            raise "add_service requires NSService object"
        for i in self.nodes:
            if i.name == svc.name:
                return
        self.nodes.append(svc)

    def set_name(self, name):
        self.name = name

    def __getitem__(self, key):
        # allow people to find things in groups via a dict style
        for i in self.nodes:
            if i.name == key:
                return i
        raise KeyError

    def __iter__(self):
        return self.nodes.__iter__()

    def output_crap(self):
        ret = ''
        for i in self.nodes:
            ret += i.output_crap()
        return ret

    def get_real(self):
        ret = []
        for i in self.nodes:
            for real in i.get_real():
                ret.append(real)
        return ret

    def output(self):
        ret = []
        for i in self.nodes:
            zone = ''
            if self.zone:
                zone = "\"%s\"" % self.zone
            ret.append('set group %s %s "%s" add "%s"' % (self.type, zone, self.name, i.name))
        return ret

class SRXApplications(JuniperSRX):
    """
    Note: May not be needed for SRX

    Container for built-in service entries and their defaults.

    Example:
        service = NSService(name="stupid_http")
        service.set_source_port((1,65535))
        service.set_destination_port(80)
        service.set_protocol('tcp')
        print service.output()
    """
    def __init__(self, entries=None):
        self.entries = entries or []
        if entries:
            self.entries = entries

        defaults = [
            ('HTTP', 'tcp', (0, 65535), (80, 80)),
            ('HTTPS','tcp', (0, 65535), (443, 443)),
            ('FTP',  'tcp', (0, 65535), (21, 21)),
            ('SSH',  'tcp', (0, 65535), (22, 22)),
            ('SNMP', 'udp', (0, 65535), (161, 162)),
            ('DNS',  'udp', (0, 65535), (53, 53)),
            ('NTP',  'udp', (0, 65535), (123, 123)),
            ('PING', 'icmp', 0, 8),
            ('SYSLOG','udp', (0, 65535), (514, 514)),
            ('MAIL','tcp', (0, 65535), (25, 25)),
            ('SMTP','tcp', (0, 65535), (25, 25)),
            ('LDAP', 'tcp', (0, 65535), (389, 389)),
            ('TFTP', 'udp', (0, 65535), (69, 69)),
            ('TRACEROUTE', 'udp', (0, 65535), (33400, 34000)),
            ('DHCP-Relay', 'udp', (0, 65535), (67, 68)),
            ('ANY',  0, (0,65535), (0, 65535)),
            ('TCP-ANY', 'tcp', (0, 65535), (0, 65535)),
            ('UDP-ANY', 'udp', (0, 65535), (0, 65535)),
            ('ICMP-ANY', 'icmp', (0, 65535), (0, 65535)),
        ]

        for (name,proto,src,dst) in defaults:
            self.entries.append(NSService(name=name, protocol=proto,
                source_port=src, destination_port=dst, predefined=True))

    def has_key(self, key):
        for entry in self.entries:
            if key == entry.name:
                return True
        return False

    def __iter__(self):
        return self.entries.__iter__()

    def __getitem__(self, item):

        for entry in self.entries:
            if item == entry.name:
                return entry

        raise KeyError("%s", item)

    def append(self, item):
        if isinstance(item, NSService):
            return self.entries.append(item)
        if isinstance(item, NSGroup) and item.type == 'service':
            return self.entries.append(item)
        raise "item inserted into NSServiceBook, not an NSService or " \
            "NSGroup.type='service' object"

    def output(self):
        ret = []
        for ent in self.entries:
            for line in ent.output():
                ret.append(line)
        return ret

class SRXAddressBook(JuniperSRX):
    """
    Container for address book entries.
    """
    def __init__(self, name="ANY", zone=None):
        self.entries = {}
        self.any = SRXAddress(name="ANY")

    def find(self, address, zone):

        if not self.entries.has_key(zone):
            return None

        for srxaddr in self.entries[zone]:
            if isinstance(address, IPy.IP):
                if srxaddr.addr == address:
                    return srxaddr 
            elif isinstance(address, str):
                isany = address.lower()
                if isany == 'any':
                    return self.any
                if srxaddr.name == address:
                    return srxaddr 

        return None

    def append(self, item):
        if not isinstance(item, SRXaddress) and \
          ((not isinstance(item, NSGroup)) and item.type != 'address'):
            raise "Item inserted int NSAddress not correct type"

        zone = item.zone # TODO: remove zones. SRX does them differently...

        if not self.entries.has_key(item.zone):
            self.entries[item.zone] = [ ]

        return self.entries[item.zone].append(item)

    def name2ips(self, name, zone):
        for entry in self.entries:
            if entry.name == name:
                if isinstance(entry, SRXAddress):
                    return [entry.addr]
                if isinstance(entry, NSGroup):
                    ret = []
                    for ent in entry:
                        ret.append(ent.addr)
                    return ret

    def output(self):
        ret = []
        for zone, addrs in self.entries.iteritems():
            for addr in addrs:
                for x in addr.output():
                    ret.append(x)
        return ret

class SRXAddress(JuniperSRX):
    """
    Container for individual address items.
    """

class SRXApplication(JuniperSRX):
    """
    Container for individual application items.
    """
    def __init__(self, name=None, protocol=None, source_port=(1,65535),
                 destination_port=(1,65535), timeout=0, predefined=False):
        self.protocol         = protocol
        self.source_port      = source_port
        self.destination_port = destination_port
        self.timeout          = timeout
        self.name             = name
        self.predefined       = predefined
        self.initialize()

    def initialize(self):
        self.set_name(self.name)
        self.set_protocol(self.protocol)
        self.set_source_port(self.source_port)
        self.set_destination_port(self.destination_port)
        self.set_timeout(self.timeout)

    def __cmp__(self, other):
        if not isinstance(other, NSService):
            return -1

        for a,b in {
            self.protocol:other.protocol,
            self.source_port:other.source_port,
            self.destination_port:other.destination_port}.iteritems():

            if a < b:
                return -1
            if a > b:
                return 1

        return 0

    def set_name(self, arg):
        self.name = arg

    def set_source_port(self, ports):
        if isinstance(ports, int):
            check_range([ports], 0, 65535)
            self.source_port = (ports, ports)
        elif isinstance(ports, tuple):
            check_range(ports, 0, 65535)
            self.source_port = ports
        else:
            raise "add_source_port needs int or tuple argument"

    def set_destination_port(self, ports):
        if isinstance(ports, int):
            check_range([ports], 0, 65535)
            self.destination_port = (ports, ports)
        elif isinstance(ports, tuple):
            check_range(ports, 0, 65535)
            self.destination_port = ports
        else:
            raise "add_destination_port needs int or tuple argument"

    def set_timeout(self, timeout):
        self.timeout = timeout

    def set_protocol(self, protocol):
        if isinstance(protocol, str) or isinstance(protocol, int):
            self.protocol = Protocol(protocol)
        if isinstance(protocol, Protocol):
            self.protocol = protocol

    def output_crap(self):
        return "[Service: %s (%d-%d):(%d-%d)]" % (self.protocol,
            self.source_port[0], self.source_port[1],
            self.destination_port[0], self.destination_port[1])

    def get_real(self):
        return [(self.source_port, self.destination_port, self.protocol)]

    def output(self):
        if self.predefined:
            return []
        ret = 'set service "%s" protocol %s src-port %d-%d ' \
              'dst-port %d-%d' % (self.name, self.protocol,
                self.source_port[0], self.source_port[1],
                self.destination_port[0], self.destination_port[1])
        if self.timeout:
            ret += ' timeout %d' % (self.timeout)
        return [ret]

class SRXRawPolicy(object):
    """
    Container for policy definitions.
    """
    def __init__(self, data, isglobal=0):
        self.isglobal = isglobal
        self.data = {}

        for entry in data:
            for key,val in entry.iteritems():
                self.data[key] = val

class SRXPolicy(JuniperSRX):
    """
    Container for individual policy definitions.
    """
    def __init__(self, name=None, source_zone="untrust",
                 destination_zone="trust", id=0, action='permit',
                 isglobal=False):
        self.source_zone      = source_zone
        self.destination_zone = destination_zone
        self.source_addresses      = []
        self.destination_addresses = []
        self.matching_applications = []
        self.action                = action

        self.id   = id
        self.name = name
        self.isglobal = isglobal

    def add_address(self, address, zone, address_book, addresses):
        addr = TIP(address)
        found = address_book.find(addr, zone)
        if not found:
            if addr.prefixlen() == 32:
                name = 'h%s' % (addr.strNormal(0))
            else:
                name = 'n%s' % (addr.strNormal())

            found = NSAddress(name=name, zone=zone, addr=addr.strNormal())

            address_book.append(found)
        addresses.append(found)

    def add_source_address(self, address):
        self.add_address(address, self.source_zone,
            self.address_book, self.source_addresses)

    def add_destination_address(self, address):
        self.add_address(address, self.destination_zone,
            self.address_book, self.destination_addresses)

    def add_application(self, protocol, source_port=(1, 65535), destination_port=(1, 65535)):
        found = None
        if not protocol:
            raise "no protocol defined in add_application"

        if isinstance(destination_port, tuple):
            sname = "%s%d-%d" % (protocol, destination_port[0],
                destination_port[1])
        else:
            sname = "%s%d" % (protocol, destination_port)

        test_application = NSService(name=sname, source_port=source_port,
                                 destination_port=destination_port,
                                 protocol=protocol)

        for svc in self.service_book:
            if svc == test_service:
                found = svc
                break

        if not found:
            self.service_book.append(test_service)
            found = test_service
        self.matching_applications.append(found)

    def __getitem__(self, key):
        if key == 'dst-address':
            return self.destination_addresses
        if key == 'src-address':
            return self.source_addresses
        if key == 'application':
            return self.matching_applications
        raise KeyError

    def output_crap(self):
        out = []
        for application in self.matching_applications:
            for src in self.source_addresses:
                for dst in self.destination_addresses:
                    print src.output_crap(),"->",dst.output_crap(),":",application.output_crap()

    def output_human(self):
        source_addrs = []
        dest_addrs   = []
        dest_serv    = []
        serv_hash    = {}

        for i in self.source_addresses:
            for addr in i.get_real():
                source_addrs.append(addr)

        for i in self.destination_addresses:
            for addr in i.get_real():
                dest_addrs.append(addr)

        for i in self.matching_applications:
            for serv in i.get_real():
                #(1, 65535), (80, 80), <Protocol: tcp>
                (s,d,p) = serv

                if not serv_hash.has_key(p):
                    serv_hash[p] = {s:[d]}

                else:
                    if not serv_hash[p].has_key(s):
                        serv_hash[p][s] = [d]
                    else:
                        serv_hash[p][s].append(d)

                dest_serv.append(serv)

        for protocol in serv_hash:
            print "protocol %s" % protocol
            for source_ports in serv_hash[protocol]:
                print " source ports", source_ports
                dest_ports = serv_hash[protocol][source_ports]
                #for dest_ports in serv_hash[protocol][source_ports]:
                print "  dest ports", dest_ports
                term = create_trigger_term(
                        source_ips   = source_addrs,
                        dest_ips     = dest_addrs,
                        source_ports = [source_ports],
                        dest_ports   = dest_ports,
                        protocols    = [protocol])
                for line in term.output(format='junos'):
                    print line


        print "SOURCES",source_addrs
        print "DESTINATIONS",dest_addrs
        print "SERVICES", serv_hash

    def output_terms(self):
        source_addrs = []
        dest_addrs   = []
        dest_serv    = []
        terms        = []
        serv_hash    = {}

        for i in self.source_addresses:
            for addr in i.get_real():
                source_addrs.append(addr)

        for i in self.destination_addresses:
            for addr in i.get_real():
                dest_addrs.append(addr)

        for i in self.matching_applications:
            for serv in i.get_real():
                (s,d,p) = serv
                if not serv_hash.has_key(p):
                    serv_hash[p] = {s:[d]}
                else:
                    if not serv_hash[p].has_key(s):
                        serv_hash[p] = {s:[d]}
                    else:
                        serv_hash[p][s].append(d)

                dest_serv.append(serv)

        for protocol in serv_hash:
            for source_ports in serv_hash[protocol]:
                dest_ports = serv_hash[protocol][source_ports]
                term = create_trigger_term(
                        source_ips   = source_addrs,
                        dest_ips     = dest_addrs,
                        source_ports = [source_ports],
                        dest_ports   = dest_ports,
                        protocols    = [protocol])
                terms.append(term)
        return terms

    def output(self):
        toret = []
        num_saddrs   = len(self.source_addresses)
        num_daddrs   = len(self.destination_addresses)
        num_matching_applications = len(self.matching_applications)
        ret = 'set policy '
        if self.isglobal:
            ret += 'global '
        if self.id:
            ret += 'id %d ' % (self.id)
        if self.name:
            ret += 'name "%s" ' % (self.name)
        ret += 'from "%s" to "%s" ' % (self.source_zone, self.destination_zone)
        for setter in [self.source_addresses,
                       self.destination_addresses,
                       self.matching_applications]:
            if not len(setter):
                ret += '"ANY" '
            else:
                ret += '"%s" ' % (setter[0].name)
        ret += '%s' % self.action
        toret.append(ret)

        if num_saddrs > 1 or num_daddrs > 1 or num_matching_applications > 1:
            toret.append("set policy id %d" % (self.id))
            for k,v in {'src-address':self.source_addresses[1:],
                        'dst-address':self.destination_addresses[1:],
                        'application':self.matching_applications[1:]}.iteritems():
                for item in v:
                    toret.append(' set %s "%s"' % (k, item.name))
            toret.append('exit')
        return toret
