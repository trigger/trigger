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
class_name = 'ShowVersion'

def xmlrpc_show_version(creds, devices):
    """Run 'show version' on the specified list of `devices`"""
    log.msg('Creating ShowVersion')
    sc = ShowVersion(devices=devices, creds=creds)
    log.msg('Done creating ShowVersion')
    d = sc.run()
    return d

class ShowVersion(CommandoApplication):
    """Simple example to run ``show version`` on devices."""
    commands = ['show version']
