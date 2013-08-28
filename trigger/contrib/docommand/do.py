#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
do - Run commands on network devices.
"""

import os
import re
import socket
from trigger.cmds import Commando
from twisted.python import log
from xml.etree.cElementTree import ElementTree, Element, SubElement
import xml.etree.cElementTree as ET

class Do(Commando):
    """
    Run commands on network devices.

    Usage::

        n = Config(devices=['dev1',dev2'], files=['file1','file2'])
        n.run()

    This will load all listed config files ('file1' and 'file2')
    onto all listed devices ('dev1,'dev2')

    :param devices:
        List of device names. Each hostname must have a match in NetDevices.

    :param files:
        List of filenames named after the FQDN of each device. 

        + Files *must* exist in a tftp-directory for non-Juniper devices.
        + Files *must* be accessible by device via tftp for non-Juniper devices.
    """
    def __init__(self, files=None, commands=None, debug=False, timeout=30, **args):
        '''
        adding files,debug to allowed arguments
        '''
        if files is None:
            files = []
        if commands is None:
            commands = []

        self.commands = commands
        self.data = {}
        self.files = files
        self.debug = debug
        self.__loadCmdsFromFiles()

        if 'args' in locals():
            args['timeout'] = timeout
        else:
            args = dict(timeout=timeout)
        Commando.__init__(self, **args)

    def __loadCmdsFromFiles(self):
        """self = __loadCmdsFromFiles()"""
        '''
        reads in file contents and adds to self.commands list
        This is done to prevent having to read the list of cmds multiple times
        '''
        while len(self.files):
            file = self.files.pop(0)
            with open(file,'r') as fr:
                lines = fr.readlines()
            for cmd in lines:
                cmd = cmd.strip()
                self.commands.append(cmd)
        return self

    def set_data(self, device, data):
        """
        Another method for storing results. If you'd rather just change the
        default method for storing results, overload this. All default
        parse/generate methods call this."""
        devname = device.nodeName
        if self.verbose:
            print "parsing <unknown> commands for "+devname
        if self.debug:
            #print "-->set_data(data="+str(data)+",device='"+devname+"')"
            msg = "-->set_data(data=%r, device=%r)" % (data, devname)
            print msg
            log.msg(msg)

        cmds = self.commands
        outs = []
        for i, out in enumerate(data):
            cmd = cmds[i]
            d = {'cmd': cmd, 'out':out, 'dev':device}
            outs.append(d)
        self.data[devname] = outs
        return True

    def __children_with_namespace(self, ns):
        return lambda elt, tag: elt.findall('./' + ns + tag)

    def from_juniper(self, data, device):
        devname = device.nodeName
        ns = '{http://xml.juniper.net/xnm/1.1/xnm}'
        if self.verbose:
            print "parsing JunOS commands for "+devname
        if self.debug:
            print "-->from_juniper(data="+str(data)+",device='"+devname+"')"

        cmds = self.commands
        outs = []
        for i, xml in enumerate(data):
            cmd = cmds[i]
            outarr = xml_print(xml,10)
            out = "\n".join(outarr)
            d = {'cmd': cmd, 'out': out, 'dev': device}
            outs.append(d)
            if self.debug:
                print "\ndata["+str(i)+"]:"
                ET.dump(xml)
        self.data[devname] = outs
        return True

class Config(Commando):
    tftp_host = settings.TFTP_HOST
    tftp_ip = socket.gethostbyname(tftp_host)
    tftp_dir = settings.TFTP_DIR

    known_commands = {
        'config':{
            'BROCADE':'conf t',
            'FOUNDRY':'conf t',
            'CISCO':'conf t',
            'JUNIPER':'configure',
            'DELL':'configure',
            'ARISTA NETWORKS':'conf t',
            'A10':'conf t'
        },
        'save_config':{
            'BROCADE':'wr mem',
            'FOUNDRY':'wr mem',
            'CISCO':'wr mem',
            'JUNIPER':'commit and-quit',
            'DELL':'copy runn start',
            'ARISTA NETWORKS':'wr mem',
            'A10':'wr mem'
        }
    }

    def __init__(self, files=[], commands=[], debug=False, **args):
        '''
        adding files,debug to allowed arguments
        '''
        self.data = {}
        self.commands = commands
        self.files = files
        self.debug = debug
        Commando.__init__(self, **args)

    def to_juniper(self,device=None,commands=None,extra=None):
        """list(str) cmds = to_juniper()"""
        '''
        device is not yet passed by Commando, but it would be nice if it were!
        '''
        if self.verbose:
            print "generating JunOS commands"
        files = self.files
        cmds = [Element('lock-configuration')]
        for fname in files:
            '''
            Again, fname is required to contain the full path
            '''
            lc = Element('load-configuration', action='replace', format='text')
            body = SubElement(lc, 'configuration-text')
            if self.debug:
                print "fname: "+fname
            body.text = file(fname).read()
            cmds.append(lc)
        #commands = self.commands
        if len(commands)>0:
            lc = Element('load-configuration', action='replace', format='text')
            body = SubElement(lc, 'configuration-text')
            body.text = "\n".join(commands)
            cmds.append(lc)
        cmds.append(Element('commit-configuration'))
        if self.debug:
            for xml in cmds:
                ET.dump(xml)
        return cmds

    def set_data(self, device, data):
        """
        Another method for storing results. If you'd rather just change the
        default method for storing results, overload this. All default
        parse/generate methods call this."""
        devname = device.nodeName
        if self.verbose:
            print "parsing <unknown> commands for "+devname
        if self.debug:
            print "-->set_data(data="+str(data)+",device='"+devname+"')"
        out = "\n".join(data)
        self.data[devname] = [{'dev':device,'cmd':'load-configuration','out':out}]
        return True

    def __children_with_namespace(self, ns):
        return lambda elt, tag: elt.findall('./' + ns + tag)

    def from_juniper(self, data, device):
        devname = device.nodeName
        if self.verbose:
            print "parsing JunOS commands for "+devname
        if self.debug:
            print "-->from_juniper(data="+str(data)+",device='"+devname+"')"
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
                success = success+1
                msg = "Success!"
            for err in res.getiterator(ns + 'error'):
                error = error+1
                msg = "ERROR: "
                elin = children(err, 'line-number')[0].text
                emes = children(err, 'message')[0].text
                ecol = children(err, 'column')[0].text
                etok = children(err, 'token')[0].text
                msg = msg + emes + " in '" + etok + "'\n    line:"+elin+",col:"+ecol
        if success:
            self.data[devname] = [{'dev':device,'cmd':'load-configuration','out':'Success'}]
        if error:
            self.data[devname] = [{'dev':device,'cmd':'load-configuration','out':msg}]
        return True

def xml_print(xml,iter):
    ## Can't find a way to tie this output to the setting of the
    ## 'DEBUG' without making it an instance method
    #print "-->xml_print(xml="+str(xml)+",iter="+str(iter)+")"
    ret = []
    if xml == None:
        print "No Data"
        return
    if iter < 1:
        return [str(xml)]
    tag = xml.tag
    marr = re.match(r"{http.*}",tag)
    ns = marr.group(0)
    tag = tag.replace(ns,'')
    ret.append(tag)
    children = list(xml)
    if len(children) < 1:
        ptxt = tag+" : "+xml.text
        return [ptxt]
    for child in children:
        ptxts = xml_print(child,10-1)
        for t in ptxts:
            ret.append("  "+t)
            ## The above shows in a tree format
            ## The below shows in a tag1 -> tag2 -> tag3 -> field:value format
            #ret.append(tag+" -> "+t)
    return ret

