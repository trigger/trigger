=======
Plugins
=======

This document describes the use and creation of plugins.

.. contents::
    :local:
    :depth: 2

Using Plugins
=============

Installation
------------
Plugins are installed like any other python package on the system.
Be sure to note the absolute path where the plugin is installed.

Inclusion
---------

Permanent
~~~~~~~~~
In your ''/etc/trigger/settings.py'' file, add the absolute path
of the plugin to the COMMANDO_PLUGINS variable as a list::

    COMMANDO_PLUGINS = [
        'trigger.contrib.config_device', 
        'trigger.contrib.show_clock', 
        'bacon.cool_plugin'
    ]

Testing
~~~~~~~
If you are testing, you can easily add your new package to the list by appending the 
new package to the COMMANDO_PLUGINS variable::

    from trigger.conf import settings
    settings.COMMANDO_PLUGINS.append('mrawesome.plugin.bacon')

from within your test script.

CLI
~~~

Work in progress.  The idea is to ssh to the server (via manhole) into a python interactive shell.


Updating
--------
If you want to install a new version of a plugin, first, you much update the plugin package on all workers and servers.

Restarting the trigger processes on all workers and servers will pick up 
the new version automatically.

Alternatively, you can use the CLI method above with the optional 'force=True' argument to force Trigger 
to reload the module without restarting any processes.


Creating
========

A plugin to be used for Trigger/Commando is a standalone python module.  The loading of a plugin will create both a Celery task as well as an XMLRPC method.

The module is required at a minimum to define::

    task_name
    xmlrpc_<task_name>

A super simple example::

    from trigger.contrib.commando import CommandoApplication
    
    task_name = 'show_version'
    def xmlrpc_show_version(*args,**kwargs):
        sc = ShowVersion(*args,**kwargs)
        d = sc.run()
        return d
    
    class ShowVersion(CommandoApplication):
        commands = ['show version']


Useful Modules
--------------

+ trigger.contrib.commando.CommandoApplication

    CommandoApplication is the base class for creating plugins that run
    commands on network devices.

+ trigger.utils.xmltodict

    This is https://github.com/martinblech/xmltodict included here for convenience.

+ trigger.utils.strip_juniper_namespace

    strip_juniper_namespace provides a post_processing script to strip
    juniper namespace.  This is useful because the namespace makes parsing the JunOS XML
    a horrible experience, especially because JunOS embeds the software version into
    the namespace.

Examples
--------
Using xmltodict to process Juniper xml output::
    
    class ShowUptime(CommandoApplication):

        def to_juniper(self, dev, commands=None, extra=None):
            cmd = Element('get-system-uptime-information')
            self.commands = [cmd]
            return self.commands
    
        def from_juniper(self, data, device):
            for xml in data:
                jdata = xmltodict.parse(
                    ET.tostring(xml),
                    postprocessor=strip_juniper_namespace,
                    xml_attribs=False
                )
                sysupinfo = jdata['rpc-reply']['system-uptime-information']
                currtime = sysupinfo['current-time']['date-time']
                res = {'current-time':currtime}
                results.append(res)
            self.store_results(device, results)



