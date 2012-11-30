# -*- coding: utf-8 -*-

"""
This is used by :doc:`../usage/scripts/go` to execute commands upon login to a
device. A user may specify a list of commands to execute for each vendor. If
the file is not found, or the syntax is bad, no commands will be passed to the
device.

By default, only a very limited subset of root commands are allowed to be
specified within the ``.gorc``. Any root commands not explicitly permitted will
be filtered out prior to passing them along to the device.

The only public interface to this module is `~trigger.gorc.get_init_commands`.
Given a ``.gorc`` That looks like this::

    cisco:
        term mon
        terminal length 0
        show clock

This is what is returned::

    >>> from trigger import gorc
    >>> gorc.get_init_commands('cisco')
    ['term mon', 'terminal length 0', 'show clock']

You may also pass a list of commands as the ``init_commands`` argument to the
`~trigger.twister.connect` function (or a `~trigger.netdevices.NetDevice`
object's method of the same name) to override anything specified in a user's
``.gorc``::

    >>> from trigger.netdevices import NetDevices
    >>> nd = NetDevices()
    >>> dev = nd.find('foo1-abc')
    >>> dev.connect(init_commands=['show clock', 'exit'])
    Connecting to foo1-abc.net.aol.com.  Use ^X to exit.

    Fetching credentials from /home/jathan/.tacacsrc
    foo1-abc#show clock
    22:48:24.445 UTC Sat Jun 23 2012
    foo1-abc#exit
    >>>

"""

# Imports
import ConfigParser
import os
import sys
from twisted.python import log

# Constants
GORC_FILE = '~/.gorc'
GORC_PATH = os.path.expanduser(GORC_FILE)
INIT_COMMANDS_SECTION = 'init_commands'

# The only root commands that are allowed to be executed. They will be filtered
# out by filter_commands()
ALLOWED_COMMANDS = (
    'set', 'show', 'get', 'ping', 'traceroute', 'who', 'whoami', 'monitor',
    'term', 'terminal', 'cli',
)


# Exports
#__all__ = ('get_init_commands',)


# Functions
def read_config(filepath=GORC_PATH):
    """
    Read the .gorc file

    :param filepath: The path to the .gorc file
    :returns: A parsed ConfigParser object
    """
    config = ConfigParser.RawConfigParser()
    try:
        status = config.read(filepath)
        if filepath not in status:
            log.msg('File not found: %r' % filepath)
            return None
    except (ConfigParser.MissingSectionHeaderError, ConfigParser.ParsingError) as err:
        log.msg(err, debug=True)
        return None
    else:
        return config

    raise RuntimeError('Something went crazy wrong with read_config()')

def filter_commands(cmds):
    """
    Filters out root commands that are not explicitly allowed by
    ``ALLOWED_COMMANDS`` and returns the filtered list.

    :param cmds:
        A list of commands that should be filtered

    :returns:
        filtered list of commands
    """
    ret = []
    for cmd in cmds:
        root = cmd.split()[0]
        if root in ALLOWED_COMMANDS:
            ret.append(cmd)
        else:
            log.msg('init_command not allowed: %r' % cmd, debug=True)
    return ret

def parse_commands(vendor, section=INIT_COMMANDS_SECTION, config=None):
    """
    Fetch the init commands.

    :param vendors:
        A vendor name (e.g. 'juniper')

    :param section:
        The section of the config

    :param config:
        A parsed ConfigParser object

    :returns:
        list of commands
    """
    if config is None:
        log.msg('No config data, not sending init commands', debug=True)
        return []

    try:
        cmdstr = config.get(section, vendor)
    except ConfigParser.NoSectionError as err:
        log.msg('%s in %s' % (err, GORC_PATH), debug=True)
        return []
    except ConfigParser.NoOptionError as err:
        log.msg(err, debug=True)
        return []
    else:
        cmds = (c for c in cmdstr.splitlines() if c != '')
        cmds = filter_commands(cmds)
        return cmds

    raise RuntimeError('Something went crazy wrong with get_init_commands()')

def get_init_commands(vendor):
    """
    Return a list of init commands for a given vendor name. In all failure
    cases it will return an empty list.

    :param vendor:
        A vendor name (e.g. 'juniper')

    :returns:
        list of commands
    """
    config = read_config()
    return parse_commands(vendor, config=config)

if __name__ == '__main__':
    #os.environ['DEBUG'] = '1'
    if os.environ.get('DEBUG', None) is not None:
        log.startLogging(sys.stdout, setStdout=False)

    print get_init_commands('juniper')
    print get_init_commands('cisco')
    print get_init_commands('arista')
    print get_init_commands('foundry')
