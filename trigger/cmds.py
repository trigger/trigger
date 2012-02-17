# -*- coding: utf-8 -*-

"""
Abstracts the execution of commands on network devices.  Allows for
integrated parsing and manipulation of return data for rapid integration
to existing or newly created tools.

Commando superclass is intended to be subclassed.  More documentation soon!
"""

__author__ = 'Jathan McCollum, Eileen Tschetter, Mark Thomas'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2009-2011, AOL Inc.'

import os
import sys
import re
import time
from IPy import IP
from xml.etree.cElementTree import ElementTree, Element, SubElement
from trigger.acl import *
from trigger.netdevices import NetDevices
from trigger.twister import (execute_junoscript, execute_ioslike,
                            execute_netscaler)

# Defaults
DEBUG = False

# Exports
__all__ = ('Commando', 'NetACLInfo')


# Classes
class Commando(object):
    """
    I run commands on devices but am not much use unless you subclass me and
    configure vendor-specific parse/generate methods.
    """
    def __init__(self, devices=None, max_conns=10,
      verbose=False, timeout=30, production_only=True):
        self.curr_connections = 0
        self.reactor_running  = False
        self.devices = devices or []
        self.verbose = verbose
        self.max_conns = max_conns
        self.nd = NetDevices(production_only=production_only)
        self.jobs = []
        self.errors = {}
        self.data = {}
        self.deferrals = self._setup_jobs()
        self.timeout = timeout # in seconds

    def _decrement_connections(self, data):
        """
        Self-explanatory. Called by _add_worker() as both callback/errback
        so we can accurately refill the jobs queue, which relies on the
        current connection count.
        """
        self.curr_connections -= 1
        return True

    def set_data(self, device, data):
        """
        Another method for storing results. If you'd rather just change the
        default method for storing results, overload this. All default
        parse/generate methods call this."""
        self.data[device] = data
        return True

    #=======================================
    # Vendor-specific parse/generate methods
    #=======================================

    # Yes there is probably a better way to do this in the long-run instead of
    # individual parse/generate methods for each vendor, but this works for now.
    def _base_parse(self, data, device):
        """
        Parse output from a device. Overload this to customize this default
        behavior.
        """
        self.set_data(device, data)
        return True

    def _base_generate_cmd(self, dev=None):
        """
        Generate commands to be run on a device. If you don't overload this, it
        returns an empty list.
        """
        return []

    # TODO (jathan): Find a way to dynamically generate/call these methods
    # TODO (jathan): Methods should be prefixed with their action, not vendor

    # IOS (Cisco)
    ios_parse = _base_parse
    generate_ios_cmd = _base_generate_cmd

    # Brocade
    brocade_parse = _base_parse
    generate_brocade_cmd = _base_generate_cmd

    # Foundry
    foundry_parse = _base_parse
    generate_foundry_cmd = _base_generate_cmd

    # Juniper (JUNOS)
    junos_parse = _base_parse
    generate_junos_cmd = _base_generate_cmd

    # Citrix NetScaler
    netscaler_parse = _base_parse
    generate_netscaler_cmd = _base_generate_cmd

    # Arista
    arista_parse = _base_parse
    generate_arista_cmd = _base_generate_cmd

    # Dell
    dell_parse = _base_parse
    generate_dell_cmd = _base_generate_cmd

    def _setup_callback(self, dev):
        """
        Map execute, parse and generate callbacks to device by manufacturer.
        This is ripe for optimization, especially if/when we need to add
        support for multiple OS types/revisions per vendor.

        :param dev: NetDevice object

        Notes::

        + Arista, Brocade, Cisco, Dell, Foundry all use execute_ioslike
        + Citrix is assumed to be a NetScaler (switch)
        + Juniper is assumed to be a router/switch running JUNOS
        """
        callback_map = {
            'ARISTA NETWORKS':[dev, execute_ioslike,
                              self.generate_arista_cmd,
                              self.arista_parse],
            'BROCADE':       [dev, execute_ioslike,
                              self.generate_brocade_cmd,
                              self.brocade_parse],
            'CISCO SYSTEMS': [dev, execute_ioslike,
                              self.generate_ios_cmd,
                              self.ios_parse],
            'CITRIX':        [dev, execute_netscaler,
                              self.generate_netscaler_cmd,
                              self.netscaler_parse],
            'DELL':          [dev, execute_ioslike,
                              self.generate_dell_cmd,
                              self.dell_parse],
            'FOUNDRY':       [dev, execute_ioslike,
                              self.generate_foundry_cmd,
                              self.foundry_parse],
            'JUNIPER':       [dev, execute_junoscript,
                              self.generate_junos_cmd,
                              self.junos_parse],
        }
        result = callback_map[dev.manufacturer]

        return result

    def _setup_jobs(self):
        for dev in self.devices:
            if self.verbose:
                print 'Adding', dev

            # Make sure that devices are actually in netdevices and keep going
            try:
                devobj = self.nd.find(str(dev))
            except KeyError:
                msg = 'Device not found in NetDevices: %s' % dev
                if self.verbose:
                    print 'ERROR:', msg

                # Track the errors and keep moving
                self.errors[dev] = msg
                continue

            this_callback = self._setup_callback(devobj)
            self.jobs.append(this_callback)

    def run(self):
        """Nothing happens until you execute this to perform the actual work."""
        self._add_worker()
        self._start()

    def eb(self, x):
        self._decrement_connections(x)
        return True

    def _add_worker(self):
        work = None

        try:
            work = self.jobs.pop()
            if self.verbose:
                print 'Adding work to queue...'
        except (AttributeError, IndexError):
            #if not self.curr_connections:
            if not self.curr_connections and self.reactor_running:
                self._stop()
            else:
                if self.verbose:
                    print 'No work left.'

        while work:
            if self.verbose:
                print 'connections:', self.curr_connections
            if self.curr_connections >= self.max_conns:
                self.jobs.append(work)
                return

            self.curr_connections += 1
            if self.verbose:
                print 'connections:', self.curr_connections

            # Unpack the job parts
            #dev, execute, cmd, parser = work
            dev, execute, generate, parser = work

            # Setup the deferred object with a timeout and error printing.
            #defer = execute(dev, cmd, timeout=self.timeout, with_errors=True)
            cmds = generate(dev)
            defer = execute(dev, cmds, timeout=self.timeout, with_errors=True)

            # Add the callbacks for great justice!
            defer.addCallback(parser, dev)
            # Here we addBoth to continue on after pass/fail
            defer.addBoth(self._decrement_connections)
            defer.addBoth(lambda x: self._add_worker())
            defer.addErrback(self.eb) # If worker add fails, still decrement

            try:
                work = self.jobs.pop()
            except (AttributeError, IndexError):
                work = None

    def _stop(self):
        if self.verbose:
            print 'stopping reactor'
        self.reactor_running = False
        from twisted.internet import reactor
        reactor.stop()

    def _start(self):
        if self.verbose:
            print 'starting reactor'
        self.reactor_running = True
        from twisted.internet import reactor
        if self.curr_connections:
            reactor.run()
        else:
            if self.verbose:
                print "Won't start reactor with no work to do!"

class NetACLInfo(Commando):
    """
    Class to fetch and parse interface information. Exposes a config
    attribute which is a dictionary of devices passed to the constructor and
    their interface information.

    Each device is a dictionary of interfaces. Each interface field will
    default to an empty list if not populated after parsing.  Below is a
    skeleton of the basic config, with expected fields::

        config {
            'device1': {
                'interface1': {
                    'acl_in': [],
                    'acl_out': [],
                    'addr': [],
                    'description': [],
                    'subnets': [],
                }
            }
        }

    Interface field descriptions::

        :addr: List of IPy.IP objects of interface addresses
        :acl_in: List of inbound ACL names
        :acl_out: List of outbound ACL names
        :description: List of interface description(s)
        :subnets: List of IPy.IP objects of interface networks/CIDRs

    Example::

        >>> n = NetACLInfo(devices=['jm10-cc101-lab.lab.aol.net'])
        >>> n.run()
        Fetching jm10-cc101-lab.lab.aol.net
        >>> n.config.keys()
        [<NetDevice: jm10-cc101-lab.lab.aol.net>]
        >>> dev = n.config.keys()[0]
        >>> n.config[dev].keys()
        ['lo0.0', 'ge-0/0/0.0', 'ge-0/2/0.0', 'ge-0/1/0.0', 'fxp0.0']
        >>> n.config[dev]['lo0.0'].keys()
        ['acl_in', 'subnets', 'addr', 'acl_out', 'description']
        >>> lo0 = n.config[dev]['lo0.0']
        >>> lo0['acl_in']; lo0['addr']
        ['abc123']
        [IP('66.185.128.160')]
    """
    def __init__(self, **args):
        self.config = dict()
        Commando.__init__(self, **args)

    def IPsubnet(self, addr):
        '''Given '172.20.1.4/24', return IP('172.20.1.0/24').'''
        net, mask = addr.split('/')
        netbase = (IP(net).int() &
                   (0xffffffffL ^ (2**(32-int(mask))-1)))
        return IP('%d/%s' % (netbase, mask))

    def generate_ios_cmd(self, dev):
        """This is the "show me all interface information" command we pass to
        IOS devices"""
        return ['show  configuration | include ^(interface | ip address | ip access-group | description|!)']

    def generate_arista_cmd(self, dev):
        """
        Similar to IOS, but:

           + Arista has now "show conf" so we have to do "show run"
           + The regex used in the CLI for Arista is more "precise" so we have to change the pattern a little bit compared to the on in generate_ios_cmd

        """
        return ['show running-config | include (^interface | ip address | ip acces-group | description |!)']

    # TODO (jathan): Temp workaround for missing brocade/foundry execution.
    # Replace with dynamic "stuff"
    #generate_arista_cmd = generate_ios_cmd
    generate_brocade_cmd = generate_ios_cmd
    generate_foundry_cmd = generate_ios_cmd

    def eb(self, data):
        print "ERROR: ", data

    def generate_junos_cmd(self, dev):
        """Generates an etree.Element object suitable for use with
        JunoScript"""
        cmd = Element('get-configuration',
            database='committed',
            inherit='inherit')

        SubElement(SubElement(cmd, 'configuration'), 'interfaces')

        return [cmd]

    def ipv4_cidr_to_netmask(bits):
        """ Convert CIDR bits to netmask """
        netmask = ''
        for i in range(4):
            if i:
                netmask += '.'
            if bits >= 8:
                netmask += '%d' % (2**8-1)
                bits -= 8
            else:
                netmask += '%d' % (256-2**(8-bits))
                bits = 0
        return netmask

    def ios_parse(self, data, device):
        """Parse IOS config based on EBNF grammar"""
        self.data[device.nodeName] = data #"MY OWN IOS DATA"

        alld = ''
        awesome = ''
        for line in data:
            alld += line

        self.config[device] = parse_ios_interfaces(alld)

        return True

    # TODO (jathan): Temp workaround for missing brocade/foundry parsing.
    # Replace with dynamic "stuff"
    arista_parse = ios_parse
    brocade_parse = ios_parse
    foundry_parse = ios_parse

    def __children_with_namespace(self, ns):
        return lambda elt, tag: elt.findall('./' + ns + tag)

    def junos_parse(self, data, device):
        """Do all the magic to parse Junos interfaces"""
        self.data[device.nodeName] = data #"MY OWN JUNOS DATA"

        ns = '{http://xml.juniper.net/xnm/1.1/xnm}'
        children = self.__children_with_namespace(ns)

        xml = data[0]
        dta = {}
        for interface in xml.getiterator(ns + 'interface'):

            basename = children(interface, 'name')[0].text
            description = children(interface, 'description')
            desctext = []

            if description:
                for i in description:
                    desctext.append(i.text)

            for unit in children(interface, 'unit'):
                ifname = basename + '.' + children(unit, 'name')[0].text
                dta[ifname] = {}
                dta[ifname]['addr'] = []
                dta[ifname]['subnets'] = []
                dta[ifname]['description'] = desctext
                dta[ifname]['acl_in'] = []
                dta[ifname]['acl_out'] = []

                # Iterating the "family/inet" tree. Seems ugly.
                for family in children(unit, 'family'):
                    for family2 in family:
                        if family2.tag != ns + 'inet':
                            continue
                        for inout in 'in', 'out':
                            dta[ifname]['acl_%s' % inout] = []

                            # Try basic 'filter/xput'...
                            acl = family2.find('%sfilter/%s%sput' % (ns, ns, inout))

                            # Junos 9.x changes to 'filter/xput/filter-name'
                            if acl is not None and "    " in acl.text:
                                 acl = family2.find('%sfilter/%s%sput/%sfilter-name' % (ns, ns, inout, ns))

                            # Pushes text as variable name.  Must be a better way to do this?
                            if acl is not None:
                                acl = acl.text

                            # If we couldn't match a single acl, try 'filter/xput-list'
                            if not acl:
                                #print 'trying filter list..'
                                acl = [i.text for i in family2.findall('%sfilter/%s%sput-list' % (ns, ns, inout))]
                                #if acl: print 'got filter list'

                            # Otherwise, making single acl into a list
                            else:
                                acl = [acl]

                            # Append acl list to dict
                            if acl:
                                dta[ifname]['acl_%s' % inout].extend(acl)

                        for node in family2.findall('%saddress/%sname' % (ns, ns)):
                            ip = node.text
                            dta[ifname]['subnets'].append(self.IPsubnet(ip))
                            dta[ifname]['addr'].append(IP(ip[:ip.index('/')]))

        self.config[device] = dta
        return True


def parse_ios_interfaces(data, acls_as_list=True, auto_cleanup=True):
    """
    Walks through a IOS interface config and returns a dict of parts. Intended
    for use by trigger.cmds.NetACLInfo.ios_parse() but was written to be portable.

    @auto_cleaup: Set to False if you don't want to pass results through
    cleanup_results(). Enabled by default.
    output

    @acls_as_list: Set to False if you want acl names as strings instead of
    list members. (e.g. "ABC123" vs. ['ABC123'])
    """
    import pyparsing as pp

    # Setup
    bang = pp.Literal("!").suppress()
    anychar = pp.Word(pp.printables)
    nonbang = pp.Word(''.join([x for x in pp.printables if x != "!"]) + '\n\r\t ')
    comment = bang + pp.restOfLine.suppress()

    #weird things to ignore in foundries
    aaa_line = pp.Literal("aaa").suppress() + pp.restOfLine.suppress()
    module_line = pp.Literal("module").suppress() + pp.restOfLine.suppress()
    startup_line = pp.Literal("Startup").suppress() + pp.restOfLine.suppress()
    ver_line = pp.Literal("ver") + anychar#+ pp.restOfLine.suppress()
    #using SkipTO instead now

    #foundry example:
    #telnet@olse1-dc5#show  configuration | include ^(interface | ip address | ip access-group | description|!)
    #!
    #Startup-config data location is flash memory
    #!
    #Startup configuration:
    #!
    #ver 07.5.05hT53
    #!
    #module 1 bi-0-port-m4-management-module
    #module 2 bi-8-port-gig-module

    #there is a lot more that foundry is including in the output that should be ignored

    interface_keyword = pp.Keyword("interface")
    unwanted = pp.SkipTo(interface_keyword, include=False).suppress()

    #unwanted = pp.ZeroOrMore(bang ^ comment ^ aaa_line ^ module_line ^ startup_line ^ ver_line)

    octet = pp.Word(pp.nums, max=3)
    ipaddr = pp.Combine(octet + "." + octet + "." + octet + "." + octet)
    address = ipaddr
    netmask = ipaddr
    cidr = pp.Literal("/").suppress() + pp.Word(pp.nums, max=2)

    # Description
    desc_keyword = pp.Keyword("description")
    description = pp.Dict( pp.Group(desc_keyword + pp.Group(pp.restOfLine)) )

    # Addresses
    #cisco example:
    # ip address 172.29.188.27 255.255.255.224 secondary
    #
    #foundry example:
    # ip address 10.62.161.187/26

    ipaddr_keyword = pp.Keyword("ip address").suppress()
    secondary = pp.Literal("secondary").suppress()

    #foundry matches on cidr and cisco matches on netmask
    #netmask converted to cidr in cleanup
    ip_tuple = pp.Group(address + (cidr ^ netmask)).setResultsName('addr', listAllMatches=True)
    ip_address = ipaddr_keyword + ip_tuple + pp.Optional(secondary)

    addrs = pp.ZeroOrMore(ip_address)

    # ACLs
    acl_keyword = pp.Keyword("ip access-group").suppress()

    # acl_name to be [''] or '' depending on acls_as_list
    acl_name = pp.Group(anychar) if acls_as_list else anychar
    direction = pp.oneOf('in out').suppress()
    acl_in = acl_keyword + pp.FollowedBy(acl_name + pp.Literal('in'))
    acl_in.setParseAction(pp.replaceWith('acl_in'))
    acl_out = acl_keyword + pp.FollowedBy(acl_name + pp.Literal('out'))
    acl_out.setParseAction(pp.replaceWith('acl_out'))

    acl = pp.Dict( pp.Group((acl_in ^ acl_out) + acl_name)) + direction
    acls = pp.ZeroOrMore(acl)

    # Interfaces
    iface_keyword = pp.Keyword("interface").suppress()
    foundry_awesome = pp.Literal(" ").suppress() + anychar
    #foundry exmaple:
    #!
    #interface ethernet 6/6
    # ip access-group 126 in
    # ip address 172.18.48.187 255.255.255.255

    #cisco example:
    #!
    #interface Port-channel1
    # description gear1-mtc : AE1 : iwslbfa1-mtc-sw0 :  : 1x1000 : 172.20.166.0/24 :  :  :
    # ip address 172.20.166.251 255.255.255.0


    interface = pp.Combine(anychar + pp.Optional(foundry_awesome))

    iface_body = pp.Optional(description) + pp.Optional(acls) + pp.Optional(addrs) + pp.Optional(acls)
    #foundry's body is acl then ip and cisco's is ip then acl

    iface_info = pp.Optional(unwanted) + iface_keyword +  pp.Dict( pp.Group(interface + iface_body) ) + pp.SkipTo(bang)
    #iface_info = unwanted +  pp.Dict( pp.Group(interface + iface_body) ) + pp.SkipTo(bang)

    interfaces = pp.Dict( pp.ZeroOrMore(iface_info) )

    # And results!
    #this is where the parsing is actually happening

    try:
        results = interfaces.parseString(data)
        #print "no error on parse string"
        #print results
    except:  # (ParseException, ParseFatalException, RecursiveGrammarException): #err:
        #pass
        #print "caught some type of error"
        #print err.line
        #print " "*(err.column-1) + "^"
        #print err

        #sys.stderr.write("parseString threw an exception")
        results = dict()

    return cleanup_interface_results(results) if auto_cleanup else results

def cleanup_interface_results(results):
    """
    Takes ParseResults dictionary-like object and returns an actual dict of
    populated interface details.  The following is performed:

        * Ensures all expected fields are populated
        * Down/un-addressed interfaces are skipped
        * Bare IP/CIDR addresses are converted to IPy.IP objects
    """

    #print "in cleanup"
    #print results

    interfaces = sorted(results.keys())
    newdict = {}
    for interface in interfaces:
        #print interface
        iface_info = results[interface]

        # Skip down interfaces
        if 'addr' not in iface_info:
            continue

        newdict[interface] = {}
        new_int = newdict[interface]

        new_int['addr'] = make_ipy(iface_info['addr'])
        new_int['subnets'] = make_cidrs(iface_info.get('subnets', []) or iface_info['addr'])
        new_int['acl_in'] = list(iface_info.get('acl_in', []))
        new_int['acl_out'] = list(iface_info.get('acl_out', []))
        #new_int['description'] = ' '.join(iface_info.get('description', [])).replace(' : ', ':')
        new_int['description'] = list(iface_info.get('description', []))

    return newdict

def make_ipy(nets):
    """Given a list of 2-tuples of (address, netmask), returns a list of
    IP address objects"""
    return [IP(addr) for addr, mask in nets]

def make_cidrs(nets):
    """Given a list of 2-tuples of (address, netmask), returns a list CIDR
    blocks"""
    return [IP(addr).make_net(mask) for addr, mask in nets]

def dump_interfaces(idict):
    """Prints a dict of parsed interface results info for use in debugging"""
    for name, info in idict.items():
        print '>>>', name
        print '\t',
        if idict[name]:
            if hasattr(info, 'keys'):
                keys = info.keys()
                print keys
                for key in keys:
                    print '\t', key, ':', info[key]
            else:
                print str(info)
        else:
            print 'might be shutdown'
        print
