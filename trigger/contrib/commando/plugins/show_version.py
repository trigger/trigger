
from twisted.python import log
from trigger.contrib.commando import CommandoApplication
from trigger.utils import xmltodict, strip_juniper_namespace

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
