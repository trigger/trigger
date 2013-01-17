# -*- coding: utf-8 -*-

"""
Parses and manipulates firewall policy for Juniper NetScreen firewall devices.
Broken apart from acl.parser because the approaches are vastly different from each
other.
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
__all__ = ('NSRawPolicy', 'NSRawGroup', 'NetScreen', 'NSGroup',
           'NSServiceBook', 'NSAddressBook', 'NSAddress', 'NSService',
           'NSPolicy')

# Classes
class NetScreen(object):
    """
    Parses and generates NetScreen firewall policy.
    """
    def __init__(self):
        self.service_book   = NSServiceBook()
        self.address_book   = NSAddressBook()
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
            # netscreen shiznit
            #
            'kw_address':      ('"address"'),
            'kw_service':      ('"service"'),
            'ns_word':         ('"\\\""?, word, "\\\""?'),
            'ns_nonspace':     ('"\\\""?, nonspace, "\\\""?'),
            'ns_quoted_word':  ('"\\\"",(word,ws?)+,"\\\""', lambda x: ''.join(x)[1:-1]),
            'ns_quoted_nonspace':  ('"\\\"",(nonspace,ws?)+,"\\\""', lambda x: ''.join(x)[1:-1]),
            S('netmask_conv'): ('(ipv4, ws, ipv4) / cidr',
                                    self.netmask2cidr),
            S('portrange'):    ('digits,"-",digits',
                                lambda (x,y):
                                    (int(x), int(y))),
            S('service'):      ('"set", ws, "service", ws, ns_word, ws,' \
                                '"protocol", ws, protocol, ws, "src-port", ws, portrange, ws,' \
                                '"dst-port", ws, portrange',
                                lambda x:
                                    NSService(name=x[0], protocol=x[1], source_port=x[2],
                                    destination_port=x[3])),
            S('address'):      ('"set", ws, "address", ws, ns_nonspace, ws, ' \
                                'ns_word, ws, netmask_conv, (ws, ns_quoted_word)?',
                                lambda x: NSAddress(zone=x[0], name=x[1], addr=x[2])),
            'kw_log':    ('"log"'),
            'kw_count':  ('"count"'),
            'kw_reject': ('"reject"'),
            'kw_permit': ('"permit"'),
            'modifiers': ('("deny"/"nat"/"permit"/"reject"/"tunnel"/"log"/"count"),ws?'),
            S('policy_rule'):  ('"from", ws, ns_word, ws, "to", ws, ns_word, ws, '\
                                'ns_word, ws, ns_word, ws, ns_word, ws, modifiers+',
                                lambda x:
                                    {'src-zone':x[0], 'dst-zone':x[1],
                                    'src-address':[x[2]], 'dst-address':[x[3]],
                                    'service':[x[4]]}),
            S('src_address'):  ('"src-address", ws, ns_word',
                                lambda x: {'src-address':x[0]}),
            S('dst_address'):  ('"dst-address", ws, ns_word',
                                lambda x: {'dst-address':x[0]}),
            S('service_short'):('"service", ws, ns_word',
                                lambda x: {'service':x[0]}),
            #S('name'):         ('"name", ws, ns_quoted_word',
            S('name'):         ('"name", ws, ns_quoted_nonspace',
                                lambda x: {'name':x[0]}),
            'global':          ('"global" / "Global"',
                                lambda x: {'global':1}),
            S('policy_set_id'):     ('"set", ws, src_address / service_short / dst_address'),
            # the thing inside a policy set id 0 stuff.
            S('policy_set_id_grp'): ('(policy_set_id, ws?)+, "exit", ws', self.concatenate_grp),
            S('policy_id'):        ('"id", ws, digits',
                                lambda x: {'id':int(x[0])}),
            'policy_id_null':  ('"id", ws, digits, ws, "exit"', lambda x: {}),
            # our main policy definition.
            S('policy'):       ('"set", ws, "policy", ws,' \
                                '((global, ws)?, (policy_id, ws)?, (name, ws)?)?,' \
                                'policy_set_id_grp / policy_rule / "exit"',
                                lambda x: NSRawPolicy(x)),
            'address_group':   ('kw_address, ws, ns_word, ws, ns_word, (ws, "add", ws, ns_word)?'),
            'service_group':   ('kw_service, ws, ns_word, (ws, "add", ws, ns_word)?'),
            S('group'):        ('"set", ws, "group", ws, address_group / service_group',
                                    lambda x:NSRawGroup(x[0])),
            '>line<':          ('ws?, service / address / group / policy, ws?'),
            S('netscreen'):    ('(line)+', self.handle_raw_netscreen)
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

    def concatenate_grp(self, x):
        """Used by NetScreen class when grouping policy members."""
        ret = {}
        for entry in x:
            for key, val in entry.iteritems():
                if key in ret:
                    ret[key].append(val)
                else:
                    ret[key] = [val]
        return ret

    def netmask2cidr(self, iptuple):
        """Converts dotted-quad netmask to cidr notation"""
        if len(iptuple) == 2:
            addr, mask = iptuple
            ipstr = addr.strNormal() + '/' + mask.strNormal()
            return TIP(ipstr)
        return TIP(iptuple[0].strNormal())

    def handle_raw_netscreen(self,rows):
        """
        The parser will hand it's final output to this function, which decodes
        and puts everything in the right place.
        """
        for node in rows:
            if isinstance(node, NSAddress):
                self.address_book.append(node)
            elif isinstance(node, NSService):
                self.service_book.append(node)
            elif isinstance(node, NSGroup):
                if node.type == 'address':
                    self.address_book.append(node)
                elif node.type == 'service':
                    self.service_book.append(node)
                else:
                    raise "Unknown NSGroup type: %s" % node.type
            elif isinstance(node, NSRawGroup):
                # take a raw parsed group entry,
                # try to find it's entry in either the addressbook,
                # or the service book. update and append to the group
                # with the proper addresses/services
                zone = None
                type = None
                name = None
                entry = None

                if len(node) == 4:
                    (type, zone, name, entry) = node
                else:
                    (type, name, entry) = node

                if entry == None:
                    continue

                if type =='address':
                    address_find = self.address_book.find(entry, zone)
                    group_find   = self.address_book.find(name, zone)
                    # does the thing being added have an entry?
                    if not address_find:
                        raise "GROUP ADD: no address book entry for %s" % (entry)

                    if group_find:
                        # we already have an entry for this group? if so
                        # just append.
                        group_find.append(address_find)
                    else:
                        # else we have to create a new group
                        new_group = NSGroup(name=name, type='address',
                          zone=zone)
                        # insert the address entry into the group
                        new_group.append(address_find)
                        # insert the new group into the address book
                        self.address_book.append(new_group)

                elif type == 'service':
                    # do the same for service groups.
                    if not self.service_book.has_key(entry):
                        raise "GROUP ADD: no service entry for %s" % (entry)
                    found = None
                    if self.service_book.has_key(name):
                        found = self.service_book[name]
                    if not found:
                        new_grp = NSGroup(name=name, type='service')
                        new_grp.append(self.service_book[entry])
                        self.service_book.append(new_grp)
                    else:
                        found.append(self.service_book[entry])
                else:
                    raise "Unknown group type"

            elif isinstance(node, NSRawPolicy):
                policy_id = node.data.get('id', 0)
                rules     = node.data.get('rules', {})
                isglobal  = node.data.get('global', 0)

                source_zone = node.data.get('src-zone', None)
                dest_zone   = node.data.get('dst-zone', None)
                source_addr = node.data.get('src-address', [])
                dest_addr   = node.data.get('dst-address', [])
                service     = node.data.get('service', [])
                name        = node.data.get('name', None)

                found = None
                subset = False

                if policy_id and not source_zone and not dest_zone:
                    # we have an sub-addition to a policy..
                    subset = True
                    for i in self.policies:
                        if i.id == policy_id:
                            found = i
                            break
                    if not found:
                        raise "Sub policy before policy defined"
                else:
                    # create a new policy
                    found = NSPolicy(id=policy_id, isglobal=isglobal, name=name)

                if source_zone:
                    found.source_zone = source_zone

                if dest_zone:
                    found.destination_zone = dest_zone

                if source_addr:
                    for entry in source_addr:
                        t = self.address_book.find(entry, found.source_zone)
                        if t is None:
                            msg = "No address entry: %s, zone: %s, policy: %s" \
                                  % (entry, found.source_zone, found.id)
                            raise exceptions.NetScreenParseError(msg)

                        if (t.zone and found.source_zone) and t.zone != found.source_zone:
                            raise "%s has a zone of %s, while the source zone" \
                                " of the policy is %s" % (t.name, t.zone, found.source_zone)
                        found['src-address'].append(t)

                if dest_addr:
                    for entry in dest_addr:
                        t = self.address_book.find(entry, found.destination_zone)
                        if t is None:
                            msg = "No address entry: %s, zone: %s, policy: %s" \
                                  % (entry, found.destination_zone, found.id)
                            raise exceptions.NetScreenParseError(msg)

                        if (t.zone and found.destination_zone) and t.zone != found.destination_zone:
                            raise "%s has a zone of %s, while the destination zone" \
                                " of the policy is %s" % (t.name, t.zone, found.destination_zone)

                        found['dst-address'].append(t)

                if service:
                    for entry in service:
                        found['service'].append(self.service_book[entry])

                if subset == False:
                    self.policies.append(found)
            else:
                raise "Unknown node type %s" % str(type(node))

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

class NSServiceBook(NetScreen):
    """
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

class NSAddressBook(NetScreen):
    """
    Container for address book entries.
    """
    def __init__(self, name="ANY", zone=None):
        self.entries = {}
        self.any = NSAddress(name="ANY")

    def find(self, address, zone):

        if not self.entries.has_key(zone):
            return None

        for nsaddr in self.entries[zone]:
            if isinstance(address, IPy.IP):
                if nsaddr.addr == address:
                    return nsaddr
            elif isinstance(address, str):
                isany = address.lower()
                if isany == 'any':
                    return self.any
                if nsaddr.name == address:
                    return nsaddr

        return None

    def append(self, item):
        if not isinstance(item, NSAddress) and \
          ((not isinstance(item, NSGroup)) and item.type != 'address'):
            raise "Item inserted int NSAddress not correct type"

        zone = item.zone

        if not self.entries.has_key(item.zone):
            self.entries[item.zone] = [ ]

        return self.entries[item.zone].append(item)

    def name2ips(self, name, zone):
        for entry in self.entries:
            if entry.name == name:
                if isinstance(entry, NSAddress):
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

class NSAddress(NetScreen):
    """
    Container for individual address items.
    """
    def __init__(self, name=None, zone=None, addr=None, comment=None):
        self.name = None
        self.zone = None
        self.addr = TIP('0.0.0.0/0')
        self.comment = ''
        if name:
            self.set_name(name)
        if zone:
            self.set_zone(zone)
        if addr:
            self.set_address(addr)
        if comment:
            self.set_comment(comment)

    def set_address(self, addr):
        try:
            a = TIP(addr)
        except Exception, e:
            raise e
        self.addr = a

    def set_zone(self, zone):
        self.zone = zone

    def set_name(self, name):
        self.name = name

    def set_comment(self, comment):
        comment = '"%s"' % comment
        self.comment = comment

    def get_real(self):
        return [self.addr]

    def output_crap(self):
        return "[(Z:%s)%s]" % (self.zone, self.addr.strNormal())

    def output(self):
        tmpl = 'set address "%s" "%s" %s %s %s'
        output = tmpl % (self.zone, self.name, self.addr.strNormal(0),
                          self.addr.netmask(), self.comment)
        return [output]

class NSService(NetScreen):
    """
    Container for individual service items.
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

class NSRawPolicy(object):
    """
    Container for policy definitions.
    """
    def __init__(self, data, isglobal=0):
        self.isglobal = isglobal
        self.data = {}

        for entry in data:
            for key,val in entry.iteritems():
                self.data[key] = val

class NSPolicy(NetScreen):
    """
    Container for individual policy definitions.
    """
    def __init__(self, name=None, address_book=NSAddressBook(),
                 service_book=NSServiceBook(), address_groups=None,
                 service_groups=None, source_zone="Untrust",
                 destination_zone="Trust", id=0, action='permit',
                 isglobal=False):
        self.service_book     = service_book
        self.address_book     = address_book
        self.service_groups   = service_groups or []
        self.address_groups   = address_groups or []
        self.source_zone      = source_zone
        self.destination_zone = destination_zone
        self.source_addresses      = []
        self.destination_addresses = []
        self.services              = []
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

    def add_service(self, protocol, source_port=(1, 65535), destination_port=(1, 65535)):
        found = None
        if not protocol:
            raise "no protocol defined in add_service"

        if isinstance(destination_port, tuple):
            sname = "%s%d-%d" % (protocol, destination_port[0],
                destination_port[1])
        else:
            sname = "%s%d" % (protocol, destination_port)

        test_service = NSService(name=sname, source_port=source_port,
                                 destination_port=destination_port,
                                 protocol=protocol)

        for svc in self.service_book:
            if svc == test_service:
                found = svc
                break

        if not found:
            self.service_book.append(test_service)
            found = test_service
        self.services.append(found)

    def __getitem__(self, key):
        if key == 'dst-address':
            return self.destination_addresses
        if key == 'src-address':
            return self.source_addresses
        if key == 'service':
            return self.services
        raise KeyError

    def output_crap(self):
        out = []
        for service in self.services:
            for src in self.source_addresses:
                for dst in self.destination_addresses:
                    print src.output_crap(),"->",dst.output_crap(),":",service.output_crap()

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

        for i in self.services:
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

        for i in self.services:
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
        num_services = len(self.services)
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
                       self.services]:
            if not len(setter):
                ret += '"ANY" '
            else:
                ret += '"%s" ' % (setter[0].name)
        ret += '%s' % self.action
        toret.append(ret)

        if num_saddrs > 1 or num_daddrs > 1 or num_services > 1:
            toret.append("set policy id %d" % (self.id))
            for k,v in {'src-address':self.source_addresses[1:],
                        'dst-address':self.destination_addresses[1:],
                        'service':self.services[1:]}.iteritems():
                for item in v:
                    toret.append(' set %s "%s"' % (k, item.name))
            toret.append('exit')
        return toret
