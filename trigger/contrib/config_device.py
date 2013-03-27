from trigger.contrib.commando import CommandoApplication

import re
import os.path
from socket import getfqdn, gethostbyname
import xml.etree.ElementTree as ET
#from twisted.python import failure
from xml.etree.cElementTree import ElementTree, Element, SubElement
from trigger.conf import settings
## xmltodict is required to parse the juniper XML output. btw, XML must die.
from trigger.utils import xmltodict, strip_juniper_namespace

import logging
log=logging.getLogger()

class ConfigDevice(CommandoApplication):
    tftp_dir = settings.tftp_dir
    tftp_host = settings.tftp_host
    tftp_ip = gethostbyname(tftp_host)

    def __init__(self, action='replace', files=None, commands=None, debug=False, **kwargs):
        self.data=[]
        self.commands = commands
        self.files = files
        self.action = action
        ##
        ## available actions:
        ##  replace
        ##  overwrite
        ##  merge
        ##  set
        ##
        self.debug = debug
        super(ConfigDevice, self).__init__(**kwargs)
    ##
    ## to_<vendor> methods
    ## 
    ## Used to construct the cmds sent to specific devices.
    ## The dev is passed to allow for creating different
    ## commands based on model and version!!

    def to_cisco(self, dev, commands=None, extra=None):
        cmds = []
        files = self.files
        for fn in files:
            copytftpcmd = "copy tftp://%s/%s running-config" % (tftp_ip,fn)
            cmds.append(copytftpcmd)
        cmds.append('copy running-config startup-config')
        return cmds
    to_arista = to_cisco

    def to_brocade(self, dev, commands=None, extra=None):
        cmds = []
        action = self.action
        files = self.files
        if re.match(r"^BRMLXE",dev.make):
            log.warn('Device Type (%s %s) not supported' % (dev.manufacturer,dev.make))
            return []
        for fn in files:
            copytftpcmd = "copy tftp running-config %s %s" % (tftp_ip,fn)
            if action == 'overwrite':
                copytftpcmd += ' overwrite'
            cmds.append(copytftpcmd)
        cmds.append('copy running-config startup-config')
        return cmds

    def to_dell(self, dev, commands=None, extra=None):
        cmds = []
        files = self.files
        if dev.make is not 'POWERCONNECT':
            log.warn('Device Type (%s %s) not supported' % (dev.manufacturer,dev.make))
            return cmds
        for fn in files:
            copytftpcmd = "copy tftp://%s/%s running-config" % (tftp_ip,fn)
            cmds.append(copytftpcmd)
        cmds.append('copy running-config startup-config')
        return cmds

    def to_a10(self, dev, commands=None, extra=None):
        cmds = []
        files = self.files
        log.warn('Device Type (%s) not supported' % dev.manufacturer)
        return cmds

    def to_juniper(self, dev, commands=None, extra=None):
        if commands is None:
            commands = []
        cmds = [Element('lock-configuration')]
        files = self.files
        action = self.action
        if action == 'overwrite':
            action = 'override'
        for fname in files:
            log.debug("fname: %s" % fname)
            filecontents = ''
            if not os.path.isfile(fname):
                fname = tftp_dir + fname
            try:
                filecontents = file(fname).read()
            except IOError as e:
                log.warn("Unable to open file: %s" % fname)
            if filecontents == '':
                continue
            lc = Element('load-configuration', action=action, format='text')
            body = SubElement(lc, 'configuration-text')
            body.text = filecontents
            cmds.append(lc)
        if len(commands)>0:
            lc = Element('load-configuration', action=action, format='text')
            body = SubElement(lc, 'configuration-text')
            body.text = "\n".join(commands)
            cmds.append(lc)
        cmds.append(Element('commit-configuration'))
        return cmds

    def from_juniper(self, data, device):
        """Do all the magic to parse Junos interfaces"""
        #print 'device:',device
        #print 'data len:',len(data)
        self.raw = data
        results = []
        for xml in data:
            jdata = xmltodict.parse(
                ET.tostring(xml),
                postprocessor=strip_juniper_namespace,
                xml_attribs=False
            )
            ##
            ## Leaving jdata structure native until I have a chance
            ##  to look at it (and other vendors' results) and restructure 
            ##  into something sane.
            ## At that point, I will want to make sure that all vendors
            ##  return a dict with the same structure.
            ##
            self.data.append({'device':device,'data':jdata})
            results.append(jdata)
        self.store_results(device, results)
