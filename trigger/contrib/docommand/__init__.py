#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
trigger.contrib.docommand
~~~~~~~~~~~~~~~~~~~~~~~~~

This package provides facilities for running commands on devices using the CLI.
"""

__author__ = 'Jathan McCollum, Mike Biancianello'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan@gmail.com'
__copyright__ = 'Copyright 2012-2013, AOL Inc.; 2013 Salesforce.com'
__version__ = '3.2.1'


# Imports
import os
import re
import socket
from twisted.python import log
from trigger.conf import settings
from trigger.cmds import Commando
from xml.etree.cElementTree import ElementTree, Element, SubElement
import xml.etree.cElementTree as ET


# Exports
__all__ = ['DoCommandBase', 'CommandRunner', 'ConfigLoader', 'xml_print', 'core']
from . import core
from core import *
__all__.extend(core.__all__)


# Classes
class DoCommandBase(Commando):
    """
    Base class for docommand action classes.

    """
    description = 'Insert description here.'

    def errback(self, failure, device):
        failure = super(DoCommandBase, self).errback(failure, device)
        print '%s - Error: %s' % (device, failure.value)
        return failure

    def from_base(self, results, device, commands=None):
        """Call store_results without calling map_results"""
        log.msg('Received %r from %s' % (results, device))
        self.store_results(device, results)


# TODO: Right now if you are loading commands from files, this will ultimately
# fail with a ReactorNotRestartable error because the core.main() function is
# calling each action class separately. We need to account for this. See
# https://gist.github.com/jathanism/4543974 for a possible solution.
class CommandRunner(DoCommandBase):
    """
    Run commands on network devices.

    Usage::

        n = CommandRunner(devices=['dev1', dev2'], files=['file1', 'file2'])
        n.run()

    This will execute all commands inside of each file ('file1','file2')
    onto all listed devices ('dev1, 'dev2').

    :param devices:
        List of device names. Each hostname must have a match in NetDevices.

    :param files:
        List of files named after the FQDN of each device.
    """
    description = 'Run commands on network devices.'

    def __init__(self, files=None, commands=None, debug=False, timeout=30, **kwargs):
        """
        :param files:
            List of fully-qualified paths to command files

        :param commands:
            List of commands to execute

        :param debug:
            Whether to display debug information

        :param timeout:
            Timeout in seconds
        """
        if files is None:
            files = []
        if commands is None:
            commands = []

        self.commands = commands
        self.data = {}
        self.files = files
        self.debug = debug
        self.__loadCmdsFromFiles()

        if 'kwargs' in locals():
            kwargs['timeout'] = timeout
        else:
            kwargs = dict(timeout=timeout)
        super(CommandRunner, self).__init__(**kwargs)

    def __loadCmdsFromFiles(self, skip_comments=True):
        """
        Reads in file contents and adds to self.commands list.

        This is done to prevent having to read the list of cmds multiple times.
        """
        for fname in self.files:
            with open(fname, 'r') as fr:
                lines = fr.readlines()

            if skip_comments:
                lines = [line for line in lines if not line.startswith('#')]

            for cmd in lines:
                cmd = cmd.strip()
                self.commands.append(cmd)

    def store_results(self, device, results):
        """Define how we're storing results."""
        devname = device.nodeName
        if self.verbose:
            print 'Parsing commands for %s' % devname
        if self.debug:
            msg = "-->store_results(device=%r, results=%r)" % (devname, results)
            print msg
            log.msg(msg)

        outs = []
        for i, out in enumerate(results):
            cmd = self.commands[i]
            d = {'cmd': cmd, 'out': out, 'dev': device}
            outs.append(d)
        self.data[devname] = outs
        return True

    def __children_with_namespace(self, ns):
        return lambda elt, tag: elt.findall('./' + ns + tag)

    def from_juniper(self, data, device, commands=None):
        # If we've set foce_cli, use from_base() instead
        if self.force_cli:
            return self.from_base(data, device, commands)

        devname = device.nodeName
        ns = '{http://xml.juniper.net/xnm/1.1/xnm}'
        if self.verbose:
            print 'parsing JunOS commands for %s' % devname
        if self.debug:
            print '-->from_juniper(data=%s, device=%r)' % (data, devname)

        cmds = self.commands
        outs = []
        for i, xml in enumerate(data):
            cmd = cmds[i]
            outarr = xml_print(xml, iterations=10)
            out = '\n'.join(outarr)
            d = {'cmd': cmd, 'out': out, 'dev': device}
            outs.append(d)
            if self.debug:
                print '\ndata["%s"]:' % i
                ET.dump(xml)
        self.data[devname] = outs
        return True


class ConfigLoader(Commando):
    """
    Load configuration changes on network devices.

    Usage::

        n = ConfigLoader(devices=['dev1', dev2'], files=['file1', 'file2'])
        n.run()

    This will load all listed config files ('file1','file2')
    onto all listed devices ('dev1, 'dev2').

    :param files:
        List of files named after the FQDN of each device.

        + Files *must* exist in a local TFTP directory for non-Juniper devices.
        + Files *must* be accessible by device via TFTP for non-Juniper devices.
    """
    description = 'Load configuration changes on network devices.'

    # These are the only officially supported vendors at this time
    vendors = ['a10', 'arista', 'brocade', 'cisco', 'foundry', 'dell',
               'juniper']

    # TODO: The config commands should be moved into NetDevice object
    # (.configure_commands). The save commands are already managed like that,
    # but we don't yet have a way to account for Juniper CLI commit command (it
    # assumes JunoScript). We need to not be hard-coding these types of things
    # all over the code-base.
    known_commands = {
        'config':{
            'a10': 'configure terminal',
            'arista': 'configure terminal',
            'brocade': 'configure terminal',
            'cisco': 'configure terminal',
            'dell': 'configure',
            'foundry': 'configure terminal',
            'juniper': 'configure',
        },
        'save_config':{
            'a10': 'write memory',
            'arista': 'write memory',
            'brocade': 'write memory',
            'cisco': 'write memory',
            'dell': 'copy running-config startup-config',
            'foundry': 'write memory',
            'juniper': 'commit and-quit',
        }
    }

    def __init__(self, files=None, commands=None, debug=False, **kwargs):
        """
        :param files:
            List of filenames named after the FQDN of each device.

        :param commands:
            List of commands to execute

        :param debug:
            Whether to display debug information
        """
        if files is None:
            files = []
        if commands is None:
            commands = []
        self.data = {}
        self.commands = commands
        self.files = files
        self.debug = debug
        super(ConfigLoader, self).__init__(**kwargs)

    def to_juniper(self, device=None, commands=None, extra=None):
        """
        Configure a Juniper device using JunoScript.

        :returns:
            list
        """
        if self.verbose:
            print "generating JunOS commands"
        files = self.files
        cmds = [Element('lock-configuration')]
        for fname in files:
            # fname is required to contain the full path
            lc = Element('load-configuration', action='replace', format='text')
            body = SubElement(lc, 'configuration-text')
            if self.debug:
                print "fname: " + fname
            body.text = file(fname).read()
            cmds.append(lc)
        #commands = self.commands
        if len(commands) > 0:
            lc = Element('load-configuration', action='replace', format='text')
            body = SubElement(lc, 'configuration-text')
            body.text = '\n'.join(commands)
            cmds.append(lc)
        cmds.append(Element('commit-configuration'))
        if self.debug:
            for xml in cmds:
                ET.dump(xml)
        return cmds

    def store_results(self, device, results):
        """
        Store the results from a commands.

        If you'd rather just change the default method for storing results,
        overload this. All default parse/generate methods call this.
        """
        devname = device.nodeName
        if self.verbose:
            print 'Parsing commands for %s' % devname
        if self.debug:
            print '-->store_results(device=%r, results=%r)' % (devname, results)
        out = '\n'.join(results)
        self.data[devname] = [{'dev': device, 'cmd': 'load-configuration', 'out': out}]
        return True

    def __children_with_namespace(self, ns):
        return lambda elt, tag: elt.findall('./' + ns + tag)

    def from_juniper(self, data, device, commands=None):
        """Parse results from a Juniper device."""
        devname = device.nodeName
        if self.verbose:
            print "parsing JunOS commands for %s " % devname
        if self.debug:
            print '-->from_juniper(data=%s, device=%r)' % (data, devname)
        if self.debug:
            for xml in data:
                ET.dump(xml)
        ns = '{http://xml.juniper.net/xnm/1.1/xnm}'
        children = self.__children_with_namespace(ns)
        confresxml = data[1]
        success = 0
        error = 0
        msg = ''
        for res in confresxml.getiterator(ns + 'load-configuration-results'):
            for succ in res.getiterator(ns + 'load-success'):
                success += 1
                msg = "Success!"
            for err in res.getiterator(ns + 'error'):
                error += 1
                msg = "ERROR: "
                elin = children(err, 'line-number')[0].text
                emes = children(err, 'message')[0].text
                ecol = children(err, 'column')[0].text
                etok = children(err, 'token')[0].text
                msg = msg + emes + " in '" + etok + "'\n    line:"+elin+",col:"+ecol
                msg = "%s %s in %r\n    line: %s, col: %s" % (msg, emes, etok,
                                                              elin, ecol)
        if success:
            self.data[devname] = [{'dev': device, 'cmd': 'load-configuration', 'out': 'Success'}]
        if error:
            self.data[devname] = [{'dev': device, 'cmd': 'load-configuration', 'out': msg}]
        return True


# Functions
def xml_print(xml, iterations=10):
    """
    Display XML in a tree format.

    :param xml:
        XML object to parse

    :param iterations:
        Number of iterations to perform
    """
    # TODO: Can't find a way to tie this output to the setting of the 'DEBUG'
    # without making it an instance method. How!!
    ret = []
    if xml is None:
        print "No Data"
        return None
    if iterations < 1:
        return [str(xml)]
    tag = xml.tag
    marr = re.match(r"{http.*}", tag)
    ns = marr.group(0)
    tag = tag.replace(ns, '')
    ret.append(tag)
    children = list(xml)

    if len(children) < 1:
        ptxt = tag + " : " + (xml.text or '')
        return [ptxt]

    for child in children:
        ptxts = xml_print(child, iterations - 1)
        for t in ptxts:
            # Shows elements in a tree format
            ret.append("  " + t)
            # Show elements in a tag1 -> tag2 -> tag3 -> field:value format
            #ret.append(tag+" -> "+t)
    return ret
