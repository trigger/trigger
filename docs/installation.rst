============
Installation
============

This is a work in progress. Please bear with us as we expand and improve this
documentation. If you have any feedback, please don't hesitate to `contact us
<http://trigger.readthedocs.org/en/latest/index.html#getting-help>`_!!

Dependencies
============

In order for Trigger's core functionality to work, you will need the primary
pieces of software:

* the Python programming language (version 2.6 or higher);
* the ``setuptools`` packaging/installation library;
* the Redis key-value server (and companion Python interface);
* the ``IPy`` IP address parsing library;
* the PyASN1 library;
* the PyCrypto cryptography library;
* and the Twisted event-driven networking engine.

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

PyASN1
------

`PyASN1 <http://pyasn1.sourceforge.net/>`_ is a dependency of Twisted Conch
which implements Abstract Syntax Notation One (`ASN.1
<http://en.wikipedia.org/wiki/Abstract_Syntax_Notation_1x>`_) and is used to
encode/decode public & private OpenSSH keys.

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

.. _redis-install:

Redis
-----

Trigger uses Redis_ as a datastore for ACL information including device
associations and the integrated change queue. Please follow the instructions
on the Redis site to get Redis running.

If you're using Ubuntu, it's as simple as::

    sudo apt-get install redis-server

.. _Redis: http://redis.io/download

The `Python redis <http://pypi.python.org/pypi/redis>`_ client is required
to interact with Redis.

Trigger currently assumes that you're running Redis on localhost and on the
default port (``6379``). If you would like to change this, update
:setting:`REDIS_HOST` in ``settings.py`` to reflect the IP address or hostname
of your Redis instance.

.. note::
    You may globally disable the use of Redis for loading ACL associations by
    setting :setting:`WITH_ACLS` to ``False``. Several libraries that interact
    with devices also have a ``with_acls`` argument to toggle this at runtime.

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

We strongly recommend using `pip <http://pypi.python.org/pypi/pip>`_ to install
Trigger as it is newer and generally better than ``easy_install``. In either
case, these tools will automatically install of the dependencies for you
quickly and easily.

Other Dependencies
------------------

Know for now that if you want to use the integrated load queue, you may
potentially require an additional database library.

See :ref:`db-drivers` below for more information.

Installing Trigger
==================

The following steps will get you the very basic functionality and will be
improved over time. As mentioned at the top of this document, if you have any
feedback or questions, please get `get in touch
<http://trigger.readthedocs.org/en/latest/index.html#getting-help>`_!

Install Trigger package
-----------------------

Using `pip <http://pypi.python.org/pypi/pip>`_::

    sudo pip install trigger

From source (which will use ``easy_install``)::

    sudo python setup.py install

Create configuration directory
------------------------------

Trigger expects to find its configuration files to be in ``/etc/trigger``. This
can be customized using the :setting:`PREFIX` configuration variable within
``settings.py``::

    sudo mkdir /etc/trigger

That's it! Now you're ready to configure Trigger.

Basic Configuration
===================

.. warning::
    For these steps you'll need to download the `Trigger tarball
    <https://github.com/trigger/trigger/tarball/develop>`_, expand it, and then
    navigate to the root directory (the same directory in which you'll find
    ``setup.py``).

Copy settings.py
----------------

Trigger expects ``settings.py`` to be in ``/etc/trigger``::

    sudo cp configs/trigger_settings.py /etc/trigger/settings.py

If you really don't like this, you may override the default location by setting
the environment variable ``TRIGGER_SETTINGS`` to the desired location. If you
go this route, you must make sure all Trigger-based tools have this set prior
to any imports!

Copy metadata file
------------------

Trigger's `~trigger.netdevices` module expects to find the device metadata file
in :setting:`PREFIX`. This file provides Trigger with information about your
devices and is at the core of Trigger’s device interaction. Anything that
communicates with devices relies on the metadata stored within this file.

For the purpose of basic config, we'll just use the sample ``netdevices.json`` file::

    sudo cp configs/netdevices.json /etc/trigger/netdevices.json

For more information on how Trigger uses the netdevices file please see
:doc:`usage/netdevices`.

Copy shared secret file
-----------------------

By default, Trigger's `~trigger.tacacsrc` module expects to find ``.tackf`` in
the :setting:`PREFIX`. This is the location of the file that contains the
passphrase used for the symettric encryption of user credentials within the
``.tacacsrc`` file. For starters, just use the sample file provided in the
Trigger distribution::

    sudo cp tests/data/tackf /etc/trigger/.tackf

If you're using a non-standard location, be sure to update the
:setting:`TACACSRC_KEYFILE` configuration variable within ``settings.py`` with the
location of ``.tackf``!

For more information on how Trigger uses encryption to protect credentials
please see :doc:`usage/tacacsrc`.

Copy autoacl.py
---------------

Trigger's `~trigger.acl.autoacl` module expects to find ``autoacl.py`` in the
:setting:`PREFIX`. This is used to customize the automatic ACL associations for
network devices.

::

    sudo cp configs/autoacl.py /etc/trigger/autoacl.py

If you're using a non-standard location, be sure to update the
:setting:`AUTOACL_FILE` configuration variable within ``settings.py`` with the
location of ``autoacl.py``!

Copy bounce.py
--------------

Trigger's `~trigger.changemgmt.bounce` module expects to find ``bounce.py`` in
the :setting:`PREFIX`. This module controls how change management (aka
maintenance or "bounce") windows get auto-applied to network devices.

::

    sudo cp configs/bounce.py /etc/trigger/bounce.py

If you're using a non-standard location, be sure to update the
:setting:`BOUNCE_FILE` configuration variable within ``settings.py`` with the
location of ``bounce.py``!

Verifying Functionality
=======================

.. warning::
    For these steps you'll still need to be at the root directory of the
    `Trigger tarball <https://github.com/trigger/trigger/tarball/develop>`_. If
    you haven't already, download it,  expand it, and then navigate to the root
    directory (the same directory in which you'll find ``setup.py``).

Once the dependencies are installed, fire up your trusty Python interpreter in
interactive mode and try doing stuff.

.. include:: interactive_mode.rst

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

.. warning::
    This WILL NOT work without :ref:`redis-install` installed and
    :setting:`WITH_ACLS` set to ``True``. If you have ACL support disabled, just
    skip this section.

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

Now that you've properly installed Trigger, you might want to know how to use it.
Please have a look at the :doc:`usage/index`.

Integrated Load Queue
=====================

Trigger currently uses a database for the automated ACL load queue used by the
``load_acl`` and ``acl`` utilities.

The supported databases are `MySQL <http://www.mysql.com/>`_, `PostgreSQL
<http://www.postgresql.org/>`_, and `SQLite <http://sqlite.org>`_.

SQLite is the easiest to get running because generally this module is part of
the Python standard library, and the database can be a simple file on your
system.

It's probably best to create a unique database and database user for this
purpose, but we'll leave that up to you.

If you want to use this functionality, you will need to do the following:

+ Choose your database solution
+ Create a database on it to be used by the load queue
+ If you're not using SQLite, ensure you have the database driver installed
+ Specify your database settings in ``settings.py``
+ Run the ``init_task_db`` tool
+ Profit!

.. _db-drivers:

Database Drivers
----------------

.. note::
    If you are using ``sqlite3`` you may ignore this section as the driver is
    included in the Python standard library.

Some of the database libraries are Python C extensions and so will expect
``gcc`` and a number of development libraries to be available on your system.

Generally you will need the development headers for Python and OpenSSL as well
as the development libraries for the database you're using.

PostgreSQL
~~~~~~~~~~

Your only choice is `psycopg2 <https://pypi.python.org/pypi/psycopg2>`_. This is a
Python C extension which requires compilation.

Here are some tips to install the library dependencies:

Ubuntu
    ``sudo apt-get install libpq-dev libssl-dev python-dev``

CentOS/RedHat
    ``sudo yum install postgresql-devel openssl-devel python-devel``

MySQL
~~~~~

For MySQL you have two choices:

1. `PyMySQL <https://pypi.python.org/pypi/PyMySQL>`_, a pure Python MySQL driver.
2. `MySQL-python <https://pypi.python.org/pypi/MySQL-python>`_. This is a
   Python C extension which requires compilation.

If you're using MySQL-python, here are some tips to install the library
dependencies:

Ubuntu
    ``sudo apt-get install libmysqlclient-dev libssl-dev python-dev``

CentOS/RedHat
    ``sudo yum install mysql-devel openssl-devel python-devel``

