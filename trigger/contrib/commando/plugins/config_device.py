
import os.path
import re
from socket import getfqdn, gethostbyname
from twisted.python import log
from trigger.contrib.commando import CommandoApplication
from trigger.conf import settings
from trigger.utils import xmltodict, strip_juniper_namespace
import xml.etree.ElementTree as ET
from xml.etree.cElementTree import ElementTree, Element, SubElement

task_name = 'config_device'

if not hasattr(settings, 'TFTPROOT_DIR'):
    settings.TFTPROOT_DIR = ''
if not hasattr(settings, 'TFTP_HOST'):
    settings.TFTP_HOST = ''

def xmlrpc_config_device(*args, **kwargs):
    c = ConfigDevice(*args, **kwargs)
    d = c.run()
    return d

class ConfigDevice(CommandoApplication):
    tftp_dir = settings.TFTPROOT_DIR
    tftp_host = settings.TFTP_HOST
    tftp_ip = gethostbyname(tftp_host)

    def __init__(self, action='replace', files=None, commands=None, debug=False, **kwargs):
        if commands is None:
            commands = []
        if files is None:
            files = []
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
            copytftpcmd = "copy tftp://%s/%s running-config" % (self.tftp_ip, fn)
            cmds.append(copytftpcmd)
        cmds.append('copy running-config startup-config')
        return cmds
    to_arista = to_cisco

    def to_brocade(self, dev, commands=None, extra=None):
        cmds = []
        action = self.action
        files = self.files
        if re.match(r"^BRMLXE", dev.make):
            log.msg('Device Type (%s %s) not supported' % (dev.vendor, dev.make))
            return []
        for fn in files:
            copytftpcmd = "copy tftp running-config %s %s" % (self.tftp_ip, fn)
            if action == 'overwrite':
                copytftpcmd += ' overwrite'
            cmds.append(copytftpcmd)
        cmds.append('copy running-config startup-config')
        return cmds

    def to_dell(self, dev, commands=None, extra=None):
        cmds = []
        files = self.files
        if dev.make != 'POWERCONNECT':
            log.msg('Device Type (%s %s) not supported' % (dev.vendor, dev.make))
            return cmds
        for fn in files:
            copytftpcmd = "copy tftp://%s/%s running-config" % (self.tftp_ip, fn)
            cmds.append(copytftpcmd)
        cmds.append('copy running-config startup-config')
        return cmds

    def to_a10(self, dev, commands=None, extra=None):
        cmds = []
        files = self.files
        log.msg('Device Type (%s) not supported' % dev.vendor)
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
            #log.msg("fname: %s" % fname)
            filecontents = ''
            if not os.path.isfile(fname):
                fname = tftp_dir + fname
            try:
                filecontents = file(fname).read()
            except IOError as e:
                log.msg("Unable to open file: %s" % fname)
            if filecontents == '':
                continue
            lc = Element('load-configuration', action=action, format='text')
            body = SubElement(lc, 'configuration-text')
            body.text = filecontents
            cmds.append(lc)
        if len(commands) > 0:
            lc = Element('load-configuration', action=action, format='text')
            body = SubElement(lc, 'configuration-text')
            body.text = "\n".join(commands)
            cmds.append(lc)
        cmds.append(Element('commit-configuration'))
        return cmds

    def from_juniper(self, data, device, commands=None):
        """Do all the magic to parse Junos interfaces"""
        #print 'device:', device
        #print 'data len:', len(data)
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
            self.data.append({'device':device, 'data':jdata})
            results.append(jdata)
        self.store_results(device, results)
