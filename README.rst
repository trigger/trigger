Summary
=======

Trigger is a framework and suite of tools for interfacing with network devices
and managing network configuration data. Written by the AOL Network Security
team in 2006, Trigger was originally designed to increase the speed and
efficiency of security policy management on firewalls, routers, and switches.
It has since been expanded to be a full-featured network engineering toolkit.

Trigger is written in Python utilizing the freely available Twisted
event-driven networking engine. The libraries can connect to network devices by
any available method (e.g. telnet, ssh), communicate with them in their native
interface (e.g. Juniper JunoScript, Cisco IOS), and return output.

Trigger is able to manage any number of jobs in parallel and handle output or
errors as they return. With the high number of network devices on the AOL
network this application is invaluable to performance and reliability.
Hopefully you'll find it useful for it on your network and consider
participating!

Getting Started
===============

The best way to get started is to read the documentation hosted by `Read the Docs <http://readthedocs.org>`_ at `http://trigger.readthedocs.org <http://trigger.readthedocs.org>`_.

Contributors
============

The following people have contributed to Trigger at some point during its
lifetime: 

- Jathan McCollum
- Eileen Tschetter
- Mark Ellzey Thomas
- Michael Shields
- Jeff Sullivan (for the best error message ever)
- Nick Sinopoli <https://github.com/NSinopoli> (for graciously giving us the name Trigger!)
