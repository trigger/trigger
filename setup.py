#!/usr/bin/env python

# Copyright, 2005-2013 AOL Inc.

from setuptools import setup, find_packages, Command
import glob
import os
import sys
import unittest

# Get version from pkg index
from trigger import release as __version__

# Names of required packages
requires = [
    'IPy>=0.73',
    'cryptography==1.4',
    'Twisted>=15.5.0,<17.0.0',
    'crochet==1.5.0',
    'mock==2.0.0',
    'pyasn1', # Twisted conch needs this, but doesn't say so
    'pyparsing~=2.2.0',
    'pytz',
    'SimpleParse',
    'gtextfsm',
    'redis', # The python interface, not the daemon!
    'PTable',
]

class CleanCommand(Command):
    user_options = []
    def initialize_options(self):
        self.cwd = None
    def finalize_options(self):
        self.cwd = os.getcwd()
    def run(self):
        assert os.getcwd() == self.cwd, 'Must be in package root: %s' % self.cwd
        os.system ('rm -rf ./build ./dist ./*.pyc ./*.tgz ./*.egg-info')

class TestCommand(Command):
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        # Change to project root to run tests
        project_root = os.path.dirname(__file__)
        if project_root:
            os.chdir(project_root)

        # Set up environment to point to mockup files.
        test_path = os.path.join(os.getcwd(), 'tests', 'data')
        os.environ['TRIGGER_SETTINGS'] = os.path.join(test_path, 'settings.py')
        os.environ['NETDEVICES_SOURCE'] = \
            os.path.join(test_path, 'netdevices.xml')
        os.environ['AUTOACL_FILE'] = os.path.join(test_path, 'autoacl.py')
        os.environ['BOUNCE_FILE'] = os.path.join(test_path, 'bounce.py')
        os.environ['TACACSRC'] = os.path.join(test_path, 'tacacsrc')
        os.environ['TACACSRC_KEYFILE'] = os.path.join(test_path, 'tackf')

        # Run each .py file found under tests.
        args = [unittest.__file__]
        for root, dirs, files in os.walk('tests'):
            for fn in files:
                if fn.startswith('test') and fn.endswith('.py'):
                    args.append(fn[:-3])

        # Inject tests dir into beginning of sys.path before we run the tests
        sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))
        unittest.main(None, None, args)

desc = 'Trigger is a framework and suite of tools for configuring network devices'
long_desc = '''
Trigger is a Python framework and suite of tools for interfacing with network
devices and managing network configuration and security policy. Trigger was
designed to increase the speed and efficiency of network configuration
management.
'''

setup(
    name='trigger',
    version=__version__,
    author='Jathan McCollum',
    author_email='jathanism@aol.com',
    packages=find_packages(exclude=['tests']) + ['twisted.plugins'],
    package_data={
        'twisted': ['plugins/trigger_xmlrpc.py'],
    },
    license='BSD',
    url='https://github.com/trigger/trigger',
    description=desc,
    long_description=long_desc,
    scripts=[
        'bin/acl',
        'bin/acl_script',
        'bin/aclconv',
        'bin/check_access',
        'bin/check_syntax',
        'bin/fe',
        'bin/gong',
        'bin/gnng',
        'bin/load_acl',
        'bin/netdev',
        'bin/optimizer',
        'bin/find_access',
        'bin/run_cmds',
        'tools/gen_tacacsrc.py',
        'tools/convert_tacacsrc.py',
        'tools/tacacsrc2gpg.py',
        'tools/init_task_db',
        'tools/prepend_acl_dot',
    ],
    install_requires=requires,
    keywords = [
        'Configuration Management',
        'IANA',
        'IEEE',
        'IP',
        'IP Address',
        'IPv4',
        'IPv6',
        'Firewall',
        'Network Automation',
        'Networking',
        'Network Engineering',
        'Network Configuration',
        'Network Security',
        'Router',
        'Systems Administration',
        'Security',
        'Switch',
    ],
    classifiers = [
        'Development Status :: 6 - Mature',
        'Environment :: Console',
        'Environment :: Console :: Curses',
        'Framework :: Twisted',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Other Audience',
        'Intended Audience :: Science/Research',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Telecommunications Industry',
        'Natural Language :: English',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet',
        'Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator',
        'Topic :: Security',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Networking',
        'Topic :: System :: Networking :: Firewalls',
        'Topic :: System :: Networking :: Monitoring',
        'Topic :: System :: Operating System',
        'Topic :: System :: Systems Administration',
        'Topic :: Terminals :: Telnet',
        'Topic :: Utilities',
    ],
    cmdclass={
        'test': TestCommand,
        'clean': CleanCommand
    }
)

def _refresh_twisted_plugins():
    """
    Make Twisted regenerate the dropin.cache, if possible.  This is necessary
    because in a site-wide install, dropin.cache cannot be rewritten by normal
    users.
    """
    try:
        from twisted.plugin import IPlugin, getPlugins
    except ImportError:
        pass
    else:
        list(getPlugins(IPlugin))
_refresh_twisted_plugins()
