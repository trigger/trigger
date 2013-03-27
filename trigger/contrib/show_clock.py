from trigger.contrib.commando import CommandoApplication

import re
import os.path
from socket import getfqdn, gethostbyname
import xml.etree.ElementTree as ET
#from twisted.python import failure
from xml.etree.cElementTree import ElementTree, Element, SubElement
from trigger.utils import xmltodict, strip_juniper_namespace

from twisted.python import log

task_name = 'show_clock'
class_name = 'ShowClock'

class ShowClock(CommandoApplication):
    commands = ['show clock']
    vendors = ['cisco']

def xmlrpc_show_clock(self, creds, devices):
    """Run 'show clock' on the specified list of `devices`"""
    log.msg('Creating ShowClock')
    sc = ShowClock(devices=devices, creds=creds)
    d = sc.run()
    log.msg('Deferred: %r' % d)
    return d

