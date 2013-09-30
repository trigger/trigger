=======
Trigger
=======

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

.. _examples-index:

Examples
========

.. include:: examples.rst

.. _platforms:

Supported Platforms
===================

Trigger currently officially supports devices manufactured by the following
vendors:

+ A10 Networks

  + All AX series application delivery controllers and server load balancers

+ Arista Networks

  + All 7000-family switch platforms

+ Aruba Networks

  + All Mobility Controller platforms

+ Brocade Networks

  + ADX application delivery switches
  + MLX routers
  + VDX switches

+ Citrix Systems

  + NetScaler application delivery controllers and server load balancers

+ Cisco Systems

  + All router and switch platforms running IOS
  + All switch platforms running NX-OS

+ Dell

  + PowerConnect switches

+ Force10

  + All router and switch platforms running FTOS

+ Foundry/Brocade

  + All router and switch platforms (NetIron, ServerIron, et al.)

+ Juniper Networks

  + All router and switch platforms running Junos
  + NetScreen firewalls running ScreenOS (Junos not yet supported)

It's worth noting that other vendors may actually work with the current
libraries, but they have not been tested. The mapping of supported platforms is
specified in ``settings.py`` as :setting:`SUPPORTED_PLATFORMS`. Modify it at
your own risk!

Getting Started
===============

.. _interactive-mode:

Before you begin
----------------

You might be required to tinker with some Python code. Don't worry, we'll be gentle!

.. include:: interactive_mode.rst

.. _install-docs:

Installation
------------

Stable releases of Trigger are best installed using ``pip`` or
``easy_install``; or you may download compressed source archives from any of
the official locations. Detailed instructions and links may be found on the
:doc:`installation` page.

Please keep in mind that before you can truly use Trigger, you must configure
it. This is not overly difficult, but it is an important step.

.. _config-docs:

Configuration
-------------

To configure Trigger please see :doc:`usage/configuration`. Initial
configuration is relatively easy. If you have any doubts, just start by using
the defaults that are provided in the instructions so you can start tinkering.

To take full advantage of all of the features, there are some hurdles you have
to jump through, but we are working on greatly simplifying this! This is a work
in progress, but it's not a bad start. Please have a look and give us
:ref:`feedback <help>` on how we can improve!

.. _documentation-index:

Documentation
=============

Please note that all documentation is written with users of Python 2.6 or
higher in mind. It's safe to assume that Trigger will not work properly on
Python versions earlier than Python 2.6.

For now, most of our documentation is automatically generated form the source
code documentation, which is usually very detailed. As we move along, this will
change, especially with regards to some of the more creative ways in which we
use Trigger's major functionality.

.. toctree::
    :hidden:

    changelog
    development
    examples
    installation
    interactive_mode
    license
    overview

.. _usage-docs:

Usage Documentation
-------------------

Once you've properly installed Trigger, you might want to know how to use it.
Please have a look at the
usage documentation!

.. toctree::
   :maxdepth: 1
   :glob:

   usage/*

.. _api-docs:

API Documentation
-----------------

Trigger's core API is made up of several components. For a more detailed
explanation of these components, please see the :doc:`overview`.

.. toctree::
   :maxdepth: 1
   :glob:

   api/*

.. _changelog-index:

Change Log
----------

Please see the :doc:`changelog`.

.. _roadmap:

Road Map
--------

We are using `milestones <https://github.com/trigger/trigger/issues/milestones>`_
to track Trigger's development path 30 to 90 days out. This is where we map
outstanding issues to upcoming releases and is the best way to see what's
coming!

.. _development-index:

Development
===========

Any hackers interested in improving Trigger (or even users interested in how
Trigger is put together or released) please see the :doc:`development` page. It
contains comprehensive info on :ref:`contributing <contributing>`, repository
layout, our release strategy, and more.

.. _help:

Getting Help
============

If you've scoured the :ref:`Usage <usage-docs>` and :ref:`API <api-docs>`
documentation and still can't find an answer to your question, below are
various support resources that should help. Please do at least skim the
documentation before posting tickets or mailing list questions, however!

.. _mailing-list:

Mailing list
------------

The best way to get help with using Trigger is via the `trigger-users mailing
list <https://groups.google.com/d/forum/trigger-users>`_ (Google Group). We'll
do our best to reply promptly!

.. _twitter:

Twitter
-------

Trigger has an official Twitter account, `@pytrigger
<http://twitter.com/pytrigger>`_, which is used for announcements and
occasional related news tidbits (e.g. "Hey, check out this neat article on
Trigger!").

.. _email:

Email
-----

If you don't do Twitter or mailing lists, please feel free to drop us an email
at `pytrigger@aol.com <mailto:pytrigger@aol.com>`_.

.. _bugs:

Bugs/ticket tracker
-------------------

To file new bugs or search existing ones, please use the GitHub issue tracker, located at `https://github.com/trigger/trigger/issues <https://github.com/trigger/trigger/issues>`_.

.. _irc:

IRC
---

Find us on IRC at ``#trigger`` on Freenode (`irc://irc.freenode.net/trigger
<irc://irc.freenode.net/trigger>`_).

Trigger is a Pacific coast operation, so your best chance of getting a
real-time response is during the weekdays, Pacific time.

.. _wiki:

Wiki
----

We will use GitHub's built-in wiki located at
`https://github.com/trigger/trigger/wiki <https://github.com/trigger/trigger/wiki>`_.

.. _openhatch:

OpenHatch
---------

Find Trigger on Openhatch at 
`http://openhatch.org/+projects/Trigger <http://openhatch.org/+projects/Trigger>`_!

.. _license:

License
=======

Trigger is licensed under the `BSD 3-Clause License
<http://www.opensource.org/licenses/BSD-3-Clause>`_. For the explicit details,
please see the :doc:`license` page.

About
=====

Trigger was created by `AOL's <http://dev.aol.com>`_ Network Engineering team.
With the high number of network devices on the AOL network this application is
invaluable to performance and reliability. Hopefully you'll find it useful for
it on your network and consider
participating!

To learn about Trigger's background and history as well as an overview of the
various components, please see the :doc:`overview`.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
