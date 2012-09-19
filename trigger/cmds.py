# -*- coding: utf-8 -*-

"""
This module abstracts the asynchronous execution of commands on multiple
network devices. It allows for integrated parsing and event-handling of return
data for rapid integration to existing or newly-created tools.

The `~trigger.cmds.Commando` class is designed to be extended but can still be
used as-is to execute commands and return the results as-is.

Please see the source code for `~trigger.cmds.ShowClock` class for a basic
example of one might create a subclass. Better documentation is in the works!
"""

__author__ = 'Jathan McCollum, Eileen Tschetter, Mark Thomas'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2009-2012, AOL Inc.'
__version__ = '2.0'

import datetime
import itertools
import os
import sys
from IPy import IP
from xml.etree.cElementTree import ElementTree, Element, SubElement
from twisted.python import log
from trigger.netdevices import NetDevices
from trigger.conf import settings
from trigger import exceptions


# Exports
__all__ = ('Commando', 'NetACLInfo', 'ShowClock')


# Classes
class Commando(object):
    """
    Execute commands asynchronously on multiple network devices.

    This class is designed to be extended but can still be used as-is to execute
    commands and return the results as-is.

    At the bare minimum you must specify a list of ``devices`` to interact with.
    You may optionally specify a list of ``commands`` to execute on those
    devices, but doing so will execute the same commands on every device
    regardless of platform.

    If ``commands`` are not specified, they will be expected to be emitted by
    the ``generate`` method for a given platform. Otherwise no commands will be
    executed.

    If you wish to customize the commands executed by device, you must define a
    ``to_{vendor_name}`` method containing your custom logic.

    If you wish to customize what is done with command results returned from a
    device, you must define a ``from_{vendor_name}`` method containing your
    custom logic.

    :param devices:
        A list of device hostnames or `~trigger.netdevices.NetDevice` objects

    :param commands:
        (Optional) A list of commands to execute on the ``devices``.

    :param incremental:
        (Optional) A callback that will be called with an empty sequence upon
        connection and then called every time a result comes back from the
        device, with the list of all results.

    :param max_conns:
        (Optional) The maximum number of simultaneous connections to keep open.

    :param verbose:
        (Optional) Whether or not to display informational messages to the
        console.

    :param timeout:
        (Optional) Time in seconds to wait for each command executed to return a
        result

    :param production_only:
        (Optional) If set, includes all devices instead of excluding any devices
        where ``adminStatus`` is not set to ``PRODUCTION``.

    :param allow_fallback:
        If set (default), allow fallback to base parse/generate methods when
        they are not customized in a subclass, otherwise an exception is raised
        when a method is called that has not been explicitly defined.
    """
    # Defaults to all supported vendors
    vendors = settings.SUPPORTED_VENDORS

    # Defaults to all supported platforms
    platforms = settings.SUPPORTED_PLATFORMS

    # The commands to run
    commands = []

    def __init__(self, devices=None, commands=None, incremental=None,
                 max_conns=10, verbose=False, timeout=30,
                 production_only=True, allow_fallback=True):
        if devices is None:
            raise exceptions.ImproperlyConfigured('You must specify some ``devices`` to interact with!')

        self.devices = devices
        self.commands = self.commands or (commands or []) # Always fallback to []
        self.incremental = incremental
        self.max_conns = max_conns
        self.verbose = verbose
        self.timeout = timeout # in seconds
        self.nd = NetDevices(production_only=production_only)
        self.allow_fallback = allow_fallback
        self.curr_conns = 0
        self.jobs = []
        self.errors = {}
        self.results = {}
        self.deferrals = self._setup_jobs()
        self.supported_platforms = self._validate_platforms()

    def _validate_platforms(self):
        """
        Determine the set of supported platforms for this instance by making
        sure the specified vendors/platforms for the class match up.
        """
        supported_platforms = {}
        for vendor in self.vendors:
            if vendor in self.platforms:
                types = self.platforms[vendor]
                if not types:
                    raise exceptions.MissingPlatform('No platforms specified for %r' % vendor)
                else:
                    #self.supported_platforms[vendor] = types
                    supported_platforms[vendor] = types
            else:
                raise exceptions.ImproperlyConfigured('Platforms for vendor %r not found. Please provide it at either the class level or using the arguments.' % vendor)

        return supported_platforms

    def _decrement_connections(self, data=None):
        """
        Self-explanatory. Called by _add_worker() as both callback/errback
        so we can accurately refill the jobs queue, which relies on the
        current connection count.
        """
        self.curr_conns -= 1
        return True

    def _increment_connections(self, data=None):
        """Increment connection count."""
        self.curr_conns += 1
        return True

    def _setup_jobs(self):
        """
        "Maps device hostnames to `~trigger.netdevices.NetDevice` objects and
        populates the job queue.
        """
        for dev in self.devices:
            if self.verbose:
                print 'Adding', dev

            # Make sure that devices are actually in netdevices and keep going
            try:
                devobj = self.nd.find(str(dev))
            except KeyError:
                if self.verbose:
                    msg = 'Device not found in NetDevices: %s' % dev
                    print 'ERROR:', msg

                # Track the errors and keep moving
                self.errors[dev] = msg
                continue

            # We only want to add devices for which we've enabled support in
            # this class
            if devobj.vendor not in self.vendors:
                raise exceptions.UnsupportedVendor("The vendor '%s' is not specified in ``vendors``. Could not add %s to job queue. Please check the attribute in the class object." % (devobj.vendor, devobj))

            self.jobs.append(devobj)

    def select_next_device(self, jobs=None):
        """
        Select another device for the active queue.

        Currently only returns the next device in the job queue. This is
        abstracted out so that this behavior may be customized, such as for
        future support for incremental callbacks.

        :param jobs:
            (Optional) The jobs queue. If not set, uses ``self.jobs``.

        :returns:
            A `~trigger.netdevices.NetDevice` object
        """
        if jobs is None:
            jobs = self.jobs

        return jobs.pop()

    def _add_worker(self):
        """
        Adds devices to the work queue to keep it populated with the maximum
        connections as specified by ``max_conns``.
        """
        while self.jobs and self.curr_conns < self.max_conns:
            device = self.select_next_device()

            self._increment_connections()
            if self.verbose:
                print 'connections:', self.curr_conns
                print 'Adding work to queue...'

            # Setup the async Deferred object with a timeout and error printing.
            commands = self.generate(device)
            async = device.execute(commands, incremental=self.incremental,
                                   timeout=self.timeout, with_errors=True)

            # Add the parser callback for great justice!
            async.addCallback(self.parse, device)

            # Here we addBoth to continue on after pass/fail
            async.addBoth(self._decrement_connections)
            async.addBoth(lambda x: self._add_worker())

            # If worker add fails, still decrement and track the error
            async.addErrback(self.errback, device)

        # Do this once we've exhausted the job queue
        else:
            if not self.curr_conns and self.reactor_running:
                self._stop()
            elif not self.jobs and not self.reactor_running:
                if self.verbose:
                    print 'No work left.'

    def _lookup_method(self, device, method):
        """
        Base lookup method. Looks up stuff by device manufacturer like:

            from_juniper
            to_foundry

        :param device:
            A `~trigger.netdevices.NetDevice` object

        :param method:
            One of 'generate', 'parse'
        """
        METHOD_MAP = {
            'generate': 'to_%s',
            'parse': 'from_%s',
        }
        assert method in METHOD_MAP

        desired_attr = None

        for vendor, types in self.platforms.iteritems():
            meth_attr = METHOD_MAP[method] % device.vendor
            if device.deviceType in types:
                if hasattr(self, meth_attr):
                    desired_attr = meth_attr
                    break

        if desired_attr is None:
            if self.allow_fallback:
                desired_attr = METHOD_MAP[method] % 'base'
            else:
                raise exceptions.UnsupportedVendor("The vendor '%s' had no available %s method. Please check your ``vendors`` and ``platforms`` attributes in your class object." % (device.vendor, method))

        func = getattr(self, desired_attr)
        return func

    def generate(self, device, commands=None, extra=None):
        """
        Generate commands to be run on a device. If you don't provide
        ``commands`` to the class constructor, this will return an empty list.

        Define a 'to_{vendor_name}' method to customize the behavior for each
        platform.

        :param device:
            A `~trigger.netdevices.NetDevice` object

        :param commands:
            (Optional) A list of commands to execute on the device. If not
            specified in they will be inherited from commands passed to the
            class constructor.

        :param extra:
            (Optional) A dictionary of extra data to send to the generate method for the
            device.
        """
        if commands is None:
            commands = self.commands
        if extra is None:
            extra = {}

        func = self._lookup_method(device, method='generate')
        return func(device, commands, extra)

    def parse(self, results, device):
        """
        Parse output from a device.

        Define a 'from_{vendor_name}' method to customize the behavior for each
        platform.

        :param results:
            The results of the commands executed on the device

        :param device:
            A `~trigger.netdevices.NetDevice` object
        """
        func = self._lookup_method(device, method='parse')
        return func(results, device)

    def errback(self, failure, device):
        """
        The default errback. Overload for custom behavior but make sure it
        always decrements the connections.

        :param failure:
            Usually a Twisted ``Failure`` instance.

        :param device:
            A `~trigger.netdevices.NetDevice` object
        """
        self.store_error(device, failure)
        self._decrement_connections(failure)
        return True

    def store_error(self, device, error):
        """
        A simple method for storing an error called by all default
        parse/generate methods.

        If you want to customize the default method for storing results,
        overload this in your subclass.

        :param device:
            A `~trigger.netdevices.NetDevice` object

        :param error:
            The error to store. Anything you want really, but usually a Twisted
            ``Failure`` instance.
        """
        self.errors[device.nodeName] = error
        return True

    def store_results(self, device, results):
        """
        A simple method for storing results called by all default
        parse/generate methods.

        If you want to customize the default method for storing results,
        overload this in your subclass.

        :param device:
            A `~trigger.netdevices.NetDevice` object

        :param results:
            The results to store. Anything you want really.
        """
        self.results[device.nodeName] = results
        return True

    def map_results(self, commands=None, results=None):
        """Return a dict of ``{command: result, ...}``"""
        if commands is None:
            commands = self.commands
        if results is None:
            results = []

        return dict(itertools.izip_longest(commands, results))

    @property
    def reactor_running(self):
        """Return whether reactor event loop is running or not"""
        from twisted.internet import reactor
        return reactor.running

    def _stop(self):
        """Stop the reactor event loop"""
        if self.verbose:
            print 'stopping reactor'

        from twisted.internet import reactor
        reactor.stop()

    def _start(self):
        """Start the reactor event loop"""
        if self.verbose:
            print 'starting reactor'

        if self.curr_conns:
            from twisted.internet import reactor
            reactor.run()
        else:
            if self.verbose:
                print "Won't start reactor with no work to do!"

    def run(self):
        """
        Nothing happens until you execute this to perform the actual work.
        """
        self._add_worker()
        self._start()

    #=======================================
    # Base generate (to_)/parse (from_) methods
    #=======================================

    def to_base(self, device, commands=None, extra=None):
        commands = commands or self.commands
        print 'Sending %r to %s' % (commands, device)
        return commands

    def from_base(self, results, device):
        print 'Received %r from %s' % (results, device)
        self.store_results(device, self.map_results(self.commands, results))

    #=======================================
    # Vendor-specific generate (to_)/parse (from_) methods
    #=======================================

    def to_juniper(self, device, commands=None, extra=None):
        """
        This just creates a series of ``<command>foo</command>`` elements to
        pass along to execute_junoscript()"""
        commands = commands or self.commands
        ret = []
        for command in commands:
            cmd = Element('command')
            cmd.text = command
            ret.append(cmd)

        return ret

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

    Interface field descriptions:

        :addr:
            List of ``IPy.IP`` objects of interface addresses

        :acl_in:
            List of inbound ACL names

        :acl_out:
            List of outbound ACL names

        :description:
            List of interface description(s)

        :subnets:
            List of ``IPy.IP`` objects of interface networks/CIDRs

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
        self.config = {}
        super(NetACLInfo, self).__init__(**args)

    def IPsubnet(self, addr):
        '''Given '172.20.1.4/24', return IP('172.20.1.0/24').'''
        net, mask = addr.split('/')
        netbase = (IP(net).int() &
                   (0xffffffffL ^ (2**(32-int(mask))-1)))
        return IP('%d/%s' % (netbase, mask))

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

    def errback(self, data):
        print "ERROR: ", data

    #=======================================
    # Vendor-specific generate (to_)/parse (from_) methods
    #=======================================

    def to_cisco(self, dev, commands=None, extra=None):
        """This is the "show me all interface information" command we pass to
        IOS devices"""
        return ['show  configuration | include ^(interface | ip address | ip access-group | description|!)']

    def to_arista(self, dev, commands=None, extra=None):
        """
        Similar to IOS, but:

           + Arista has now "show conf" so we have to do "show run"
           + The regex used in the CLI for Arista is more "precise" so we have to change the pattern a little bit compared to the on in generate_ios_cmd

        """
        return ['show running-config | include (^interface | ip address | ip acces-group | description |!)']

    # Other IOS-like vendors are Cisco-enough
    to_brocade = to_cisco
    to_foundry = to_cisco

    def from_cisco(self, data, device):
        """Parse IOS config based on EBNF grammar"""
        self.results[device.nodeName] = data #"MY OWN IOS DATA"

        alld = ''
        awesome = ''
        for line in data:
            alld += line

        self.config[device] = _parse_ios_interfaces(alld)

        return True

    # Other IOS-like vendors are Cisco-enough
    from_arista = from_cisco
    from_brocade = from_cisco
    from_foundry = from_cisco

    def to_juniper(self, dev, commands=None, extra=None):
        """Generates an etree.Element object suitable for use with
        JunoScript"""
        cmd = Element('get-configuration',
            database='committed',
            inherit='inherit')

        SubElement(SubElement(cmd, 'configuration'), 'interfaces')

        self.commands = [cmd]
        return self.commands

    def __children_with_namespace(self, ns):
        return lambda elt, tag: elt.findall('./' + ns + tag)

    def from_juniper(self, data, device):
        """Do all the magic to parse Junos interfaces"""
        self.results[device.nodeName] = data #"MY OWN JUNOS DATA"

        ns = '{http://xml.juniper.net/xnm/1.1/xnm}'
        children = self.__children_with_namespace(ns)

        xml = data[0]
        dta = {}
        for interface in xml.getiterator(ns + 'interface'):

            basename = children(interface, 'name')[0].text

            description = interface.find(ns + 'description')
            desctext = []
            if description is not None:
                desctext.append(description.text)

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

def _parse_ios_interfaces(data, acls_as_list=True, auto_cleanup=True):
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

def _cleanup_interface_results(results):
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

        new_int['addr'] = _make_ipy(iface_info['addr'])
        new_int['subnets'] = _make_cidrs(iface_info.get('subnets', []) or iface_info['addr'])
        new_int['acl_in'] = list(iface_info.get('acl_in', []))
        new_int['acl_out'] = list(iface_info.get('acl_out', []))
        #new_int['description'] = ' '.join(iface_info.get('description', [])).replace(' : ', ':')
        new_int['description'] = list(iface_info.get('description', []))

    return newdict

def _make_ipy(nets):
    """Given a list of 2-tuples of (address, netmask), returns a list of
    IP address objects"""
    return [IP(addr) for addr, mask in nets]

def _make_cidrs(nets):
    """Given a list of 2-tuples of (address, netmask), returns a list CIDR
    blocks"""
    return [IP(addr).make_net(mask) for addr, mask in nets]

def _dump_interfaces(idict):
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

class ShowClock(Commando):
    """
    A simple example that runs ``show clock`` and parses it to
    ``datetime.datetime`` object.
    """
    commands = ['show clock']
    vendors = ['cisco', 'brocade']

    def _parse_datetime(self, datestr, fmt):
        """
        Given a date string and a format, try to parse and return
        datetime.datetime object.
        """
        try:
            return datetime.datetime.strptime(datestr, fmt)
        except ValueError:
            return datestr

    def _store_datetime(self, results, device, fmt):
        """
        Parse and store a datetime
        """
        print 'received %r from %s' % (results, device)
        mapped = self.map_results(self.commands, results)
        for cmd, res in mapped.iteritems():
            mapped[cmd] = self._parse_datetime(res, fmt)

        self.store_results(device, mapped)

    def from_cisco(self, results, device):
        """Parse Cisco time"""
        # => '16:18:21.763 GMT Thu Jun 28 2012\n'
        fmt = '%H:%M:%S.%f %Z %a %b %d %Y\n'
        self._store_datetime(results, device, fmt)

    def from_brocade(self, results, device):
        """
        Parse Brocade time. Brocade switches and routers behave
        differently...
        """
        if device.is_router():
            # => '16:42:04 GMT+00 Thu Jun 28 2012\r\n'
            fmt = '%H:%M:%S GMT+00 %a %b %d %Y\r\n'
        elif device.is_switch():
            # => 'rbridge-id 1: 2012-06-28 16:42:04 Etc/GMT+0\n'
            results = [res.split(': ', 1)[-1] for res in results]
            fmt = '%Y-%m-%d %H:%M:%S Etc/GMT+0\n'

        self._store_datetime(results, device, fmt)
