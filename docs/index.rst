#######
Trigger
#######

*"Keep your eyes on the prize, and your finger on the trigger."*

What is Trigger?
================

Trigger is a robust network automation toolkit written in Python that was
designed for interfacing with network devices and managing network
configuration and security policy. It increases the speed and efficiency of
managing large-scale networks while reducing the risk of human error.

.. _key-features:

Key Features
============

Trigger is designed to work at scale and can support hundreds or thousands of
network devices with ease. Here are some of things that make Trigger tick:

+ Support for SSH, Telnet, and Juniper's Junoscript XML API
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

.. versionadded:: 1.2

+ Import your metadata from an existing `RANCID <http://www.shrubbery.net/rancid/>`_
  installation to get up-and-running quickly!

.. versionadded:: 1.3

+ Import your metadata from a CSV file and get up-and-running even quicker!

.. _documentation-index:

Documentation
=============

Please note that all documentation is written with users of Python 2.6 or
higher in mind. It's safe to assume that Trigger will not work properly on
Python versions earlier than Python 2.6.

For now, most of our documentation is automatically generated from the source
code documentation, which is usually very detailed. As we move along, this will
change, especially with regards to some of the more creative ways in which we
use Trigger's major functionality.

.. toctree::
    :maxdepth: 2

    overview
    platforms
    installation
    configuration
    usage/index
    examples
    api/index
    development
    license
    support
    experimental
    changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
