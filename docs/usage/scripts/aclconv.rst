#######################
aclconv - ACL Converter
#######################

About
=====

**aclconv** Convert an ACL on stdin, or a list of ACLs, from one format to another.  Input format is determined automatically.  Output format can be given with ``-f`` or with one of ``-i``/``-o``/``-j``/``-x``.  The name of the output ACL is determined automatically, or it can be specified with ``-n``.

Usage
=====

Here is the usage output::

    Options:
    -h, --help            show this help message and exit
    -f FORMAT, --format=FORMAT
    -o, --ios-named       Use IOS named ACL output format
    -j, --junos           Use JunOS ACL output format
    -i, --ios             Use IOS old-school ACL output format
    -x, --iosxr           Use IOS XR ACL output format
    -n ACLNAME, --name=ACLNAME

Examples
========

Let's start with a simple Cisco ACL:

.. code-block:: bash

   $ cat http.acl
   access-list 123 permit tcp any host 10.20.30.40 eq 80

And convert it to Juniper format:

.. code-block:: bash

   $ aclconv -j http.acl
   firewall {
   replace:
       filter 123j {
           term T1 {
               from {
                   destination-address {
                       10.20.30.40/32;
                   }
                   protocol tcp;
                   destination-port 80;
               }
               then {
                   accept;
                   count T1;
               }
           }
       }
   }

Neat, huh?
