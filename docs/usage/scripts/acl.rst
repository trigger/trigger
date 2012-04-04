============================
acl - ACL database interface
============================

.. contents::
    :local:
    :depth: 2

About
=====

**acl** is used to interface with the ACL database and queue. It is a simple
command to manage or determine access-list associations, and allows you to
inject or remove an ACL from the load queue.

Usage
=====

Here is the usage output::

    % acl
    Usage: acl [options]

    Options:
    -h, --help            show this help message and exit
    -s, --staged          list currently staged ACLs
    -l, --list            list ACLs currently in integrated (automated) queue
    -m, --listmanual      list entries currently in manual queue
    -i, --inject          inject into load queue
    -c, --clear           clear from load queue
    -x, --exact           match entire name, not just start
    -d, --device-name-only
                          don't match on ACL
    -a ADD, --add=ADD     add an acl to explicit ACL database, example: "acl -a
                          abc123 test1-abc test2-abc"
    -r REMOVE, --remove=REMOVE
                          remove an acl from explicit ACL database, example:
                          "acl -r abc123 -r xyz246 test1-abc"
    -q, --quiet           be quiet! (For use with scripts/cron)


Examples
========

Managing ACL associations
-------------------------

Adding an ACL association
~~~~~~~~~~~~~~~~~~~~~~~~~

When adding an association, you must provide the full ACL name. You may,
however, use the short name of any devices to which you'd like to associate
that ACL::

    % acl -a jathan-special test1-abc test2-abc
    added acl jathan-special to test1-abc.net.aol.com
    added acl jathan-special to test2-abc.net.aol.com

If you try to add an association for a device that does not exist, it will complain::

    % acl -a foo godzilla-router
    skipping godzilla-router: invalid device

    Please use --help to find the right syntax.

Removing an ACL association
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Removing associations are subject to the same restrictions as additions, however in this example we've referenced the devices by FQDN::

    % acl -r jathan-special test1-abc.net.aol.com test2-abc.net.aol.com
    removed acl jathan-special from test1-abc.net.aol.com
    removed acl jathan-special from test2-abc.net.aol.com

Confirm the removal and observe that it returns nothing::

     % acl jathan-special
     %

If you try to remove an ACL that is not associated, it will complain::

    % acl -r foo test1-abc
    test1-abc.net.aol.com does not have acl foo

Searching for an ACL or device
------------------------------

You may search by full or partial names of ACLs or devices. When you search for
results, ACLs are checked first. If there are no matches then device names are
checked second. In either case, the pattern must match the beginning of the name
of the ACL or device.

You may search for the exact name of the ACL we just added::

    % acl jathan-special
    test1-abc.net.aol.com                   jathan-special
    test2-abc.net.aol.com                   jathan-special

A partial ACL name will get you the same results in this case::

    % acl jathan
    test1-abc.net.aol.com                   jathan-special
    test2-abc.net.aol.com                   jathan-special

A partial name will return all matching objects with  names starting with the pattern. Because there are no ACLs starting with ``'test1'`` matching devices are returned instead::

    % acl test1
    test1-abc.net.aol.com                   jathan-special abc123 xyz246
    test1-def.net.aol.com                   8 9 10
    test1-xyz.net.aol.com                   8 9 10

If you want to search for an exact ACL match, use the ``-x`` flag::

    % acl -x jathan
    No results for ['jathan']

Or if you want to match devices names only, use the ``-d`` flag::

    % acl -d jathan-special
    No results for ['jathan-special']
    
Working with the load queue
---------------------------

Not finished yet...

Integrated queue
~~~~~~~~~~~~~~~~

Manual queue
~~~~~~~~~~~~
