.. Trigger documentation master file, created by
   sphinx-quickstart on Wed Jul  6 15:17:22 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=======
Trigger
=======

*"Go ahead, pull it!"*

About
=====

Trigger is a Python framework and suite of tools for interfacing with network
devices and managing network configuration and security policy. Trigger was
designed to increase the speed and efficiency of network configuration
management.

Trigger's core device interaction utilizes the freely available `Twisted
<http://twistedmatrix.com/>`_ event-driven networking engine. The libraries can
connect to network devices by any available method (e.g. telnet, SSH),
communicate with them in their native interface (e.g. Juniper JunoScript, Cisco
IOS), and return output. Trigger is able to manage any number of jobs in
parallel and handle output or errors as they return.

Motivation
----------

Trigger was created to facilitate rapid provisioning and automation of
firewall policy change requests by Network Security. It has since expanded to
cover all network device configuration.

The complexity of the network was increasing much more quickly than the amount
of time we had to spend on administering it, both because AOL's products and
services were becoming more sophisticated and because we were continually
expanding infrastructure. This pressure created a workload gap that had be
filled with tools that increased productivity.

Pre-Trigger tools worked only for some common cases and required extensive
knowledge of the network, and careful attention during edits and loads.
Sometimes this resulted in a system-impacting errors, and it routine work more
dangerous and unrewarding than it should have been.

With the high number of network devices on the AOL network Trigger has become
invaluable to the performance and reliability of the AOL network infrastructure.

History
-------

Trigger was originally originally written by the AOL Network Security team and
is now maintained by the Network Engineering organization.

Once upon a time Trigger was actually called **SIMIAN**, a really bad acronym
that stood for **System Integrating Management of Individual Access to
Networks**. It has since outgrown its original purpose and can be used for any
network hardware management operations, so we decided to ditch the acronym and
just go with a name that more accurately hints at what it does.

Supported Vendors
=================

Trigger currently supports devices manufactured by the following vendors:

+ Arista Networks

  + All 7000-family platforms

+ Brocade Networks

  + MLX routers and VDX switches

+ Cisco Systems

  + IOS-based platforms only including all Catalyst switches and GSR/OSR routers

+ Dell

  + PowerConnect switches

+ Foundry/Brocade

  + All router and switch platforms (NetIron, ServerIron, et al.)

+ Juniper Networks

  + All router and switch platforms running Junos
  + NetScreen firewalls running ScreenOS (Junos not yet supported)

+ Citrix Systems

  + NetScaler web accelerator switches (SSH only, no REST/SOAP yet)

Installation
============

To install Trigger, please check out the installation docs!

.. toctree::
   :maxdepth: 1

   installation

Configuration
=============

This is a work in progress, but it's not a bad start. Please have a look and give us feedback on how we can improve!

.. toctree::
  :maxdepth: 1

  configuration

Documentation
=============

Please note that all documentation is written with users of Python 2.6 in mind. It's safe to assume that Trigger will not work properly on Python versions earlier than Python 2.6.

For now, most of our documentation is automatically generated form the source code documentation, which is usually very detailed. As we move along, this will change, especially with regards to some of the more creative ways in which we use Trigger's major functionality.

.. _api-docs:

API Documentation
-----------------

Trigger's core API is made up of several components.

.. toctree::
   :maxdepth: 1
   :glob:

   api/*

.. _tutorial:

Tutorial
--------

Coming Soon.

.. _usage-docs:

Usage Documentation
-------------------

Once you've properly installed Trigger, you might want to know how to use it. Please have a look at the
usage documentation!


.. toctree::
   :maxdepth: 1
   :glob:

   usage/*

FAQ
---

You guessed it: Coming Soon.

Change Log
----------

Please review the :doc:`changelog`.

Contributing
============

Any hackers interested in improving Trigger (or even users interested in how
Trigger is put together or released) please see the :doc:`development` page. It
contains comprehensive info on contributing, repository layout, our release
strategy, and more.

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

To file new bugs or search existing ones, please use the GitHub issue tracker, located at `https://github.com/aol/trigger/issues <https://github.com/aol/trigger/issues>`_.

.. _irc:

IRC
---

IRC coming Soon™.

.. _wiki:

Wiki
----

We will use GitHub's built-in wiki located at
`https://github.com/aol/trigger/wiki <https://github.com/aol/trigger/wiki>`_.

.. _license:

License
=======

Trigger is licensed under the `Clear BSD License
<http://labs.metacarta.com/license-explanation.html>`_ which is based on the
`BSD 3-Clause License <http://www.opensource.org/licenses/BSD-3-Clause>`_, and
adds a term expressly stating it does not grant you any patent licenses.

For the explicit details, please see the :doc:`license` page.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
