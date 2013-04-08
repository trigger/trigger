from trigger.contrib.commando import CommandoApplication

import re
import os.path
from socket import getfqdn, gethostbyname
import xml.etree.ElementTree as ET
#from twisted.python import failure
from xml.etree.cElementTree import ElementTree, Element, SubElement
from trigger.utils import xmltodict, strip_juniper_namespace

from twisted.python import log

task_name = 'show_version'

def xmlrpc_show_version(*args,**kwargs):
    """Run 'show version' on the specified list of `devices`"""
    log.msg('Creating ShowVersion')
    sc = ShowVersion(*args,**kwargs)
    d = sc.run()
    return d

class ShowVersion(CommandoApplication):
    """Simple example to run ``show version`` on devices."""
    commands = ['show version']
