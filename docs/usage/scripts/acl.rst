============================
acl - ACL database interface
============================

About
=====

**acl** is used to interface with the ACL database and queue. Simple command to
determine access-list associations, also allows you to add or remove an ACL
from the load queue.

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

Here are some examples of use::

    ====Notes====
    The file "acls.db" has been removed from Trigger. To manage explicit ACL-device associations you must now use the 'acl' command.
    Two new arguments have been added to 'acl':

    <pre>
    -a ADD, --add=ADD     add an acl to explicit ACL database (expects args to
                            be device names)
    -r REMOVE, --remove=REMOVE
                            remove an acl from explicit ACL database (expects
                            args to be device names)
    </pre>
    ====EXAMPLES====
    Adding an ACL to a device or devices:
    <pre>
    % acl -a jathan-special test1-abc test2-abc
    added acl jathan-special to test1-abc.net.aol.com
    added acl jathan-special to test2-abc.net.aol.com
    </pre>
    
    Confirm the change:
    <pre>
    % acl jathan-special
    test1-abc.net.aol.com                   jathan-special
    test2-abc.net.aol.com                   jathan-special
    </pre>
    
    Removing an ACL:
    <pre>
    % acl -r jathan-special test1-abc.net.aol.com test2-abc.net.aol.com
    removed acl jathan-special from test1-abc.net.aol.com
    removed acl jathan-special from test2-abc.net.aol.com
    </pre>
    Confirm the change:
    <pre>
    % acl jathan-special
    (returns nothing)
    </pre>