What is Trigger?
================

Trigger is a robust network engineering toolkit written in Python that was
designed for interfacing with network devices and managing network
configuration and security policy. It increases the speed and efficiency of
managing large-scale networks while reducing the risk of human error.

Started by the AOL Network Security team in 2006, Trigger was originally
designed for security policy management on firewalls, routers, and switches. It
has since been expanded to be a full-featured network engineering toolkit.

With the high number of network devices on the AOL network this application is
invaluable to performance and reliability. We hope you'll find it useful on
your network and consider participating!

Key Features
============

Trigger is designed to work at scale and can support hundreds or thousands of
network devices with ease. Here are some of things that make Trigger tick:

+ Support for SSH, Telnet, and Juniper's Junoscript XML API.
+ Easily get an interactive shell or execute commands asynchronously.
+ Leverage advanced event-driven functionality to manage any number of
  jobs in parallel and handle output or errors as they return.
+ Powerful metadata interface for performing complex queries to group and
  associate network devices by name, manufacturer, type, location, and more.
+ Encrypted storage of login credentials so you can interact without constantly
  being prompted to enter your password.
+ Flexible access-list & firewall policy parser that can test access if access
  is permitted, or easily convert ACLs from one format to another.
+ Detailed support for timezones and maintenance windows.
+ A suite of tools for simplifying many common tasks.

New in version 1.2:

+ Import your metadata from an existing RANCID installation to get
  up-and-running quickly!

New in version 1.3:

+ Import your metadata from a CSV file and get up-and-running even quicker!

Getting Started
===============

The best way to get started is to read the documentation hosted by `Read the Docs <http://readthedocs.org>`_ at `http://trigger.readthedocs.org <http://trigger.readthedocs.org>`_. There you will find everything you need to get going including usage examples, installation and configuration instructions, and more!

Before you begin
----------------

+ The ``develop`` branch is the default branch, and while generally stable is
  not considered production-ready. Use at your own risk!
+ The ``master`` branch is the stable branch, and will reflect the latest
  production-ready changes. It is recommended that this is the branch you use
  if you are installing Trigger for the first time.
+ Each point release of Trigger is maintained as a tag branch. If you require a
  specific Trigger version, refer to these.

