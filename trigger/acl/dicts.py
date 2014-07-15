# -*- coding: utf-8 -*-

"""
This code is originally from parser.py. It contains all the simple data definitions in
form of dictionaries and lists and such. This file is not meant to by used by itself.
Imported into support.py.

Variables defined:

  adrsbk
  dscp_names
  fragment_flag_names
  icmp_reject_codes
  icmp_types
  icmp_codes
  ip_option_names
  ios_icmp_messages
  ios_icmp_names
  junos_match_ordering_list
  junos_match_order
  address_matches
  ports
  precedence_names
  tcp_flag_names
  tcp_flag_specials
  tcp_flag_rev
"""

__author__ = 'Jathan McCollum, Mike Biancaniello, Michael Harding, Michael Shields'
__editor__ = 'Joseph Malone'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathanism@aol.com'
__copyright__ = 'Copyright 2006-2013, AOL Inc.; 2013 Saleforce.com'

adrsbk = { 'svc':{'group':{}, 'book':{}}, 'addr':{'group':{},'book':{}} }

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

fragment_flag_names = {
    'dont-fragment': 0x4000,
    'more-fragments': 0x2000,
    'reserved': 0x8000 }

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

ip_option_names = {
    'loose-source-route': 131,
    'record-route': 7,
    'router-alert': 148,
    'strict-source-route': 137,
    'timestamp': 68 }

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
