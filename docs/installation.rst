============
Installation
============

Blurb about installation goes here.

Dependencies
============

In order for Trigger's core functionality to work, you will need the primary
pieces of software:

* the Python programming language (version 2.6 or higher);
* the ``setuptools`` packaging/installation library;
* the Redis key-value server (and companion Python interface);
* the PyCrypto cryptography library;
* and the Twisted Matrix event-driven networking engine.

Trigger has a tricky set of dependencies. If you want to take full advantage of
all of Trigger's functionality, you'll need them all. If you only want to use
certain parts, you might not need them all. Each dependency will list the
components that utilize it to help you make an informed decision.

Please read on for important details on each dependency -- there are a few
gotchas.

Python
------

Obviously Trigger requires Python. Only version 2.6 is supported, but Python 2.7
should be just fine. There is currently no official support for Python 3.x. We
cannot yet say with confidence that we have worked out all of the legacy kinks
from when Trigger was first developed against Python 2.3.

setuptools
----------

`Setuptools`_ comes with some Python installations by default; if yours doesn't,
you'll need to grab it. In such situations it's typically packaged as
``python-setuptools``, ``py26-setuptools`` or similar. Trigger will likely drop its
setuptools dependency in the future, or include alternative support for the
`Distribute`_ project, but for now setuptools is required for installation.

.. _setuptools: http://pypi.python.org/pypi/setuptools
.. _Distribute: http://pypi.python.org/pypi/distribute


PyCrypto
--------

`PyCrypto <http://www.amk.ca/python/code/crypto.html>`_ is a dependency of
Twisted Conch which provides the low-level (C-based) encryption algorithms used to
run SSH. There are a couple gotchas associated with installing PyCrypto: its
compatibility with Python's package tools, and the fact that it is a C-based
extension.

Twisted
-------

`Twisted <http://twistedmatrix.com/>`_ is huge and has a few dependencies
of its. We told you this was tricky! To make things easier, please make sure you
install the full-blown Twisted source tarball. You especially need
`Twisted Conch <http://twistedmatrix.com/trac/wiki/TwistedConch>`_, which is
used to run SSH.

Used by:

* :mod:`trigger.cmds`
* :mod:`trigger.twister`

Redis
-----

Trigger uses Redis_ as a datastore for ACL information including device
associations and the integrated change queue. Please follow the instructions
on the Redis site to get Redis running.

If you're using Ubuntu, it's as simple as::

    sudo apt-get install redis-server

.. _Redis: http://redis.io/download

The `python redis <http://pypi.python.org/pypi/redis>`_ client is required
to interact with Redis.

Trigger currently assumes that you're running Redis on localhost and on the
default port (6379). If you would like to change this, update ``REDIS_HOST`` in
`trigger_settings.py` to reflect the IP address or hostname of your Redis instance.

Used by:

* :mod:`trigger.acl.autoacl`
* :mod:`trigger.acl.db`
* :mod:`trigger.acl.tools`
* :mod:`trigger.netdevices`

IPy
---

`IPy <http://pypi.python.org/pypi/IPy>`_ is a class and tools for handling
of IPv4 and IPv6 addresses and networks. It is used by Trigger for parsing and
handling IP addresses.

Used by:

* :mod:`trigger.acl.db`
* :mod:`trigger.acl.parser`
* :mod:`trigger.acl.tools`
* :mod:`trigger.cmds`
* :mod:`trigger.conf.settings`
* :mod:`trigger.netscreen`

pytz
----

`pytz <http://pypi.python.org/pypi/pytz>`_ is an immensely powerful time zone
library for Python that allows accurate and cross platform timezone calculations.
It is used by Trigger's change management interface to allow for strict adherance
to scheduled maintenance events.

Used by:

* :mod:`trigger.acl.db`
* :mod:`trigger.changemgmt`
* :mod:`trigger.netdevices`


SimpleParse
-----------

`SimpleParse <http://pypi.python.org/pypi/SimpleParse>`_ is an extremely fast parser
generator for Python that converts EBNF grammars into parsers. It is used by Trigger's
ACL parser to allow us to translate ACLs from flat files into vendor-agnostic objects.

Used by:

* :mod:`trigger.acl.parser`

Package tools
~~~~~~~~~~~~~

We strongly recommend using ``pip`` to install Trigger as it is newer and
generally better than ``easy_install``. In either case, these tools will
automatically install of the dependencies for you quickly and easily.

Other Dependencies
------------------

This needs to be cleaned up.

+ python-mysql (MySQLdb)

Installing Trigger
==================

Install Trigger package
-----------------------

Using ``pip``::

    sudo pip install trigger

From source (which will use ``easy_install``)::

    sudo python setup.py install

Create configuration directory
------------------------------

This can be customized using the ``PREFIX`` configuration variable within ``trigger_settings.py`` and defaults to ``/usr/local/trigger``::

    sudo mkdir /usr/local/trigger

Copy trigger_settings.py
------------------------

Trigger expects ``trigger_settings.py`` to be in ``/etc``. If you really don't like
this, edit ``trigger/conf.py`` and change the value of ``SETTINGS_FILE`` prior to
installing the package::

    sudo cp conf/trigger_settings.py /etc/trigger_settings.py

Copy autoacl.py
---------------

::

    sudo cp conf/autoacl.py /usr/local/trigger/autoacl.py

If you're using a non-standard location, be sure to update the ``AUTOACL_FILE`` configuration variable within ``trigger_settings.py`` with the location of ``autoacl.py``!

Copy netdevices.xml
-------------------

::

    sudo cp conf/netdevices.xml /usr/local/trigger/netdevices.xml

Create MySQL Database
---------------------

Trigger currently (but hopefully not for too much longer) uses MySQL for the automated ACL load queue used by the ``load_acl`` and ``acl`` utilities. If you want to use these tools, you need to create a MySQL database and make sure you also have the Python `MySQLdb` module installed.

Find ``conf/acl_queue_schema.sql`` in the source distribution and import the `queue` and `acl_queue` tables into a database of your choice. It's probably best to create a unique database and database user for this purpose, but we'll leave that up to you.

Example import::

    % mysql trigger -u trigger_user -p < ./conf/acl_queue_schema.sql 

Verify Functionality
====================

Once the dependencies are installed, try doing stuff.

NetDevices
----------

Try instantiating NetDevices, which holds your device metadata::

    >>> from trigger.netdevices import NetDevices
    >>> nd = NetDevices()
    >>> dev = nd.find('test1-abc.net.aol.com')

ACL Parser
----------

Try parsing an ACL using the ACL parser (the `tests` directory can be found
within the Trigger distribution)::

    >>> from trigger.acl import parse
    >>> acl = parse(open("tests/data/acl.test"))
    >>> len(acl.terms)
    103

ACL Database
------------

Try loading the AclsDB to inspect automatic associations. First directly from autoacl::

    >>> from trigger.acl.autoacl import autoacl
    >>> autoacl(dev)
    set(['juniper-router.policer', 'juniper-router-protect'])

And then inherited from autoacl by AclsDB::

    >>> from trigger.acl.db import AclsDB
    >>> a = AclsDB()
    >>> a.get_acl_set(dev)
    >>> dev.implicit_acls
    set(['juniper-router.policer', 'juniper-router-protect'])
