.. Trigger documentation master file, created by
   sphinx-quickstart on Wed Jul  6 15:17:22 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=======
Trigger
=======

About
=====

Trigger is a Python framework and suite of tools for interfacing with network
devices and managing configuration and security policy.  Written by
the AOL Network Security team, it is designed to increase the speed
and efficiency of network configuration management.

Trigger's core device interaction utilizes the freely available `Twisted Matrix
<http://twistedmatrix.com/>`_ event-driven networking engine. The libraries can
connect to network devices by any available method (e.g. telnet, SSH),
communicate with them in their native interface (e.g. Juniper JunoScript, Cisco
IOS), and return output. Because of Twisted, Trigger is able to manage any
number of jobs in parallel and handle output or errors as they return. With the
high number of network devices on the AOL network Trigger is invaluable to
performance and reliability.

History
-------

Once upon a time Trigger was actually **SIMIAN**, a really bad acronym that stood
for **System Integrating Management of Individual Access to Networks**. Trigger
has since outgrown its original purpose and can be used for any network
hardware management operations, so we decided to ditch the acronym and just go
with a proper noun.

Motivation
----------

Trigger was created to facilitate rapid provisioning and automation of
firewall policy change requests by Network Security. It has since expanded to
cover all network device configuration. There are four major reasons
we needed this:

1. The Firewall Change Productivity Gap
    The complexity of the network was increasing much more quickly than
    the amount of time we had to spend on administering it, both because
    AOL's products and services were becoming more complex and because we
    were continually expanding our security posture. This pressure created
    a workload gap that had be filled with tools that increased
    productivity.

2. Audit Compliance
    Sarb-Ox and PCI audits meant that we had to spend more time verifying
    that requests were processed according to our documented procedures,
    and producing a paper trail of why access was required and what
    approvals were made. Product owners and Network Engineering also
    frequently requested more information about what firewall holes were
    in place and how they could move requests faster. By automating our
    common processes, we are working towards providing greater visibility
    and audit trails automatically, instead of as an independent step that
    requires additional work.

3. Complete Coverage
    Pre-Trigger tools worked only for some common cases and required
    extensive knowledge of the network, and careful attention during edits
    and loads. NetSec has had historically low turnover and so this only
    sometimes resulted in a system-impacting errors, but it made NetSec's
    routine work more dangerous and unrewarding than it should have been.

4. Human Error
    The pre-Trigger request processing error rate was about 3%, and the
    request turnaround about 48 hours. These were not bad for a fully
    manual process, but it is enough of a bottleneck to high-profile
    projects that there was much room for improvement. With a more
    transparent and automated process, we have been more responsive to
    requesters than ever.

Supported Vendors
-----------------

Trigger currently supports devices manufactured by the following vendors:


+ Cisco Systems

  + Cisco IOS-based platforms only including all Catalyst switches, GSR/OSR routers.

+ Foundry/Brocade

  + All switch/router platforms.

+ Juniper Networks

  + All routers switches running JunOS and NetScreen firewalls running ScreenOS.

+ Citrix Systems

  + NetScaler web accelerator switches.

Installation
============

Blah blah blah stuff about installing Trigger here and then link to install page.

.. toctree::
   :maxdepth: 1

   installation

Configuration
=============

.. toctree::
  :maxdepth: 1

  configuration

Documentation
=============

Please note that all documentation is written with users of Python 2.6 in mind. It's safe to assume that Trigger will not work properly on Python versions earlier than Python 2.6.

For now, most of our documentation is automatically generated form the source code documentation, which is usually very detailed. As we move along, this will change, especially with regards to some of the more creative ways in which we use Trigger's major functionality.

API Documentation
-----------------

Trigger's core API is made up of several components.

.. toctree::
   :maxdepth: 1
   :glob:

   api/*

Tutorial
--------

Coming Soon.

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

Stuff about contribuing to Trigger will go here.

Any hackers interested in improving Fabric (or even users interested in how
Fabric is put together or released) please see the :doc:`development` page. It
contains comprehensive info on contributing, repository layout, our release
strategy, and more.

Getting Help
============

Stuff about getting help with Trigger will go here. The following is ripped directly from Fabric's superb documentation and should be replaced.

If you've scoured the :ref:`prose <usage-docs>` and :ref:`API <api_docs>`
documentation and still can't find an answer to your question, below are
various support resources that should help. We do request that you do at least
skim the documentation before posting tickets or mailing list questions,
however!

Mailing list
------------

The best way to get help with using Fabric is via the `fab-user mailing list
<http://lists.nongnu.org/mailman/listinfo/fab-user>`_ (currently hosted at
``nongnu.org``.) The Fabric developers do their best to reply promptly, and the
list contains an active community of other Fabric users and contributors as
well.

Twitter
-------

Fabric has an official Twitter account, `@pyfabric
<http://twitter.com/pyfabric>`_, which is used for announcements and occasional
related news tidbits (e.g. "Hey, check out this neat article on Fabric!").

.. _bugs:

Bugs/ticket tracker
-------------------

To file new bugs or search existing ones, you may visit Fabric's `Redmine
<http://redmine.org>`_ instance, located at `code.fabfile.org
<http://code.fabfile.org>`_. Due to issues with spam, you'll need to (quickly
and painlessly) register an account in order to post new tickets.

IRC
---

We maintain a semi-official IRC channel at ``#fabric`` on Freenode
(``irc://irc.freenode.net``) where the developers and other users may be found.
As always with IRC, we can't promise immediate responses, but some folks keep
logs of the channel and will try to get back to you when they can.

Wiki
----

There is an official Fabric `MoinMoin <http://moinmo.in>`_ wiki reachable at
`wiki.fabfile.org <http://wiki.fabfile.org>`_, although as of this writing its
usage patterns are still being worked out. Like the ticket tracker, spam has
forced us to put anti-spam measures up: the wiki has a simple, easy captcha in
place on the edit form.

License
=======

Trigger is licensed under a slightly modified version of the
`BSD 3-Clause License <http://www.opensource.org/licenses/BSD-3-Clause>`_.

For the explicit details, please see the :doc:`license` page.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
