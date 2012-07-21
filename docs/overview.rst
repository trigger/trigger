========
Overview
========

This document is a high-level overview of Trigger's features and a little
history about why it exists in the first place.

.. contents::
    :local:
    :depth: 2

About
=====

Trigger is a Python framework and suite of tools for interfacing with network
devices and managing network configuration and security policy. Trigger was
designed to increase the speed and efficiency of network configuration
management.

Trigger's core device interaction utilizes the `Twisted
<http://twistedmatrix.com/>`_ event-driven networking engine. The libraries can
connect to network devices by any available method (e.g. telnet, SSH),
communicate with them in their native interface (e.g. Juniper JunoScript, Cisco
IOS), and return output. Trigger is able to manage any number of jobs in
parallel and handle output or errors as they return.

Motivation
==========

Trigger was created to facilitate rapid provisioning and automation of
firewall policy change requests by Network Security. It has since expanded to
cover all network device configuration.

The complexity of the AOL network was increasing much more quickly than the
amount of time we had to spend on administering it, both because AOL's products
and services were becoming more sophisticated and because we were continually
expanding infrastructure. This pressure created a workload gap that had be
filled with tools that increased productivity.

Pre-Trigger tools worked only for some common cases and required extensive
knowledge of the network, and careful attention during edits and loads.
Sometimes this resulted in a system-impacting errors, and it caused routine
work more dangerous and unrewarding than it should have been.

With the high number of network devices on the AOL network Trigger has become
invaluable to the performance and reliability of the AOL network infrastructure.

History
=======

Trigger was originally written by the AOL Network Security team and
is now maintained by the Network Engineering organization.

Once upon a time Trigger was actually called **SIMIAN**, a really bad acronym
that stood for **System Integrating Management of Individual Access to
Networks**. It has since outgrown its original purpose and can be used for any
network hardware configuration management operations, so we decided to ditch
the acronym and just go with a name that more accurately hints at what it does.

Components
==========

Trigger is comprised of the following core components:

NetDevices
----------

An abstract interface to network device metadata and security policy associations.

Twister
-------

Asynchronous device interaction library.  Performs login and basic command-line
interaction support via telnet or SSH using the Twisted asynchronous I/O
framework.

Access-List Parser
------------------

An ACL parsing library which contains various modules that allow for parsing,
manipulation, and management of network access control lists (ACLs). It will
parse a complete ACL and return an ACL object that can be easily translated to
any supported vendor syntax.

+ Converting ACLs from one format to another (e.g. Cisco to Juniper)
+ Testing an ACL to determine is access is permitted
+ Automatically associate ACLs to devices by metatdata


Change Management
-----------------

An abstract interface to bounce windows and moratoria. Includes support for RCS
version-control system for maintaining configuration data and an integrated
automated task queue.

Commands
--------

Command execution library which abstracts the execution of commands on network
devices. Allows for integrated parsing and manipulation of return data for
rapid integration to existing or newly created tools.

TACACSrc
--------

Network credentials library that provides an abstract interface to storing user
credentials encrypted on disk.

Command-Line Tools
------------------

Trigger includes a suite of tools for simplifying many common tasks, including:

+ Quickly get an interactive shell
+ Simple metadata search tool
