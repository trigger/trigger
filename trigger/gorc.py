# -*- coding: utf-8 -*-

# gorc.py - Read .gorc file from a user's home directory

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
    'term', 'terminal',
)


# Exports
__all__ = ('get_init_commands',)


# Functions
def read_config(filepath=GORC_PATH):
    """Read the .gorc file"""
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
    """Filters out root commands that are not explicitly allowed by
    ALLOWED_COMMANDS and returns the filtered list."""
    ret = []
    for cmd in cmds:
        root = cmd.split()[0]
        if root in ALLOWED_COMMANDS:
            ret.append(cmd)
        else:
            log.msg('init_command not allowed: %r' % cmd, debug=True)
    return ret

def parse_commands(vendor, section=INIT_COMMANDS_SECTION, config=None):
    """Fetch the init commands"""
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
    """
    config = read_config()
    return parse_commands(vendor, config=config)

if __name__ == '__main__':
    #os.environ['DEBUG'] = '1'
    if os.environ.get('DEBUG', None) is not None:
        log.startLogging(sys.stdout, setStdout=False)

    print get_init_commands('juniper')
    print get_init_commands('cisco systems')
    print get_init_commands('arista networks')
    print get_init_commands('foundry')
