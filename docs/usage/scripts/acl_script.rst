##############################################
acl_script - Modify ACLs from the command-line
##############################################

About
=====

**acl_script** is a tool and an API shipped that allows for the quick and easy
modifications of filters based on various criteria. This is used most in an
automated fashion, allowing for users to quickly and efficiently setup small
scripts to auto-generate various portions of an ACL.

Usage
=====

Here is the usage output::

    usage: acl_script [options]

    ACL modify/generator from the commandline.
    options:
      -h, --help
      -aACL, --acl=ACL      specify the acl file
      -n, --no-changes      don't make the changes
      --show-mods           show modifications being made in a simple format.
      --no-worklog          don't make a worklog entry
      -N, --no-input        require no input (good for scripts)
      -sSOURCE_ADDRESS, --source-address=SOURCE_ADDRESS
                            define a source address
      -dDESTINATION_ADDRESS, --destination-address=DESTINATION_ADDRESS
                            define a destination address
      --destination-address-from-file=DESTINATION_ADDRESS_FROM_FILE
                            read a set of destination-addresses from a file
      --source-address-from-file=SOURCE_ADDRESS_FROM_FILE
                            read a set of source-addresses from a file
      --protocol=PROTOCOL   define a protocol
      -pSOURCE_PORT, --source-port=SOURCE_PORT
                            define a source-port
      --source-port-range=SOURCE_PORT_RANGE
                            define a source-port range
      --destination-port-range=DESTINATION_PORT_RANGE
                            define a destination-port range
      -PDESTINATION_PORT, --destination-port=DESTINATION_PORT
                            define a destination port
      -tMODIFY_SPECIFIC_TERM, --modify-specific-term=MODIFY_SPECIFIC_TERM
                            When modifying a JUNOS type ACL, you may specify this
                            option one or more times to define a specific JUNOS
                            term you want to modify. This takes one argument which
                            should be the name of term.
      -cMODIFY_BETWEEN_COMMENTS, --modify-between-comments=MODIFY_BETWEEN_COMMENTS
                            When modifying a IOS type ACL, you may specify this
                            option one or more times to define a specific AREA of
                            the ACL you want to modify. You must have at least 2
                            comments defined in the ACL prior to running. This
                            requires two arguments, the start comment, and the end
                            comment. Your modifications will be done between the
                            two.
      --insert-defined      This option works differently based on the type of ACL
                            we are modifying. The one similar characteristic is
                            that this will never remove any access already defined,
                            just append.
      --replace-defined     This option works differently based on the type of ACL
                            we are modifying. The one similar characteristic is
                            that access can be removed, since this replaces whole
                            sets of defined data.


Examples
========

Understanding ``--insert-defined``
----------------------------------

This flag will tell ``acl_script`` to append (read: never remove) information
to a portion of an ACL.

Junos
~~~~~

On a Junos-type ACL using ``--insert-defined``, this will only replace parts of
the term that have been specified on the command-line. This may sound confusing
but this example should clear things up.

Take the following term::

    term sr31337 {
        from {
            source-address {
                10.0.0.0/8;
                11.0.0.0/8;
            }
            destination-address {
                192.168.0.1/32;
            }
            destination-port 80;
            protocol tcp;
        }
        then {
            accept;
            count sr31337;
        }
    }

If you run ``acl_script`` with the following arguments::

  acl_script --modify-specific-term sr31337 --source-address 5.5.5.5/32 --destination-port 81 --insert-defined

The following is generated::

    term sr31337 {
        from {
            source-address {
                5.5.5.5/32;
                10.0.0.0/8;
                11.0.0.0/8;
            }
            destination-address {
                192.168.0.1/32;
            }
            destination-port 80-81;
            protocol tcp;
        }
        then {
            accept;
            count sr31337;
        }
    }

As you can see ``5.5.5.5/32`` was added to the ``source-address`` portion, and
``81`` was added as a ``destination-port``. Notice that all other fields were
left alone.

IOS-like
~~~~~~~~

On IOS-like ACLs ``--insert-defined`` behaves a little bit differently. In this
case the ``acl_script`` will only add access where it is needed.

Take the following example::

    !!! I AM L33T
    access-list 101 permit udp host 192.168.0.1 host 192.168.1.1 eq 80
    access-list 101 permit ip host 192.168.0.5 host 192.168.1.10
    access-list 101 permit tcp host 192.168.0.6 host 192.168.1.11 eq 22
    !!! I AM NOT L33T

If you run ``acl_script`` with the following arguments::

    acl_script --modify-between-comments "I AM L33T" "I AM NOT L33T" \
      --source-address 192.168.0.5 \
      --destination-address 192.168.1.10 \
      --destination-address 192.168.1.11 \
      --protocol tcp \
      --destination-port 80 \
      --insert-defined

This output is generated::

    !!! I AM L33T
    access-list 101 permit udp host 192.168.0.1 host 192.168.1.1 eq 80
    access-list 101 permit ip host 192.168.0.5 host 192.168.1.10
    access-list 101 permit tcp host 192.168.0.6 host 192.168.1.11 eq 22
    access-list 101 permit tcp host 192.168.0.5 host 192.168.1.11 eq 80
    !!! I AM NOT L33T

As you can see the last line was added, take note that the
``192.168.0.5->192.168.1.10:80`` access was not added because it was already
permitted previously.

Understanding ``--replace-defined``
-----------------------------------

This flag will completely replace portions of an ACL with newly-defined information.

Junos
~~~~~

Take the following term::

    term sr31337 {
        from {
            source-address {
                10.0.0.0/8;
                11.0.0.0/8;
            }
            destination-address {
                192.168.0.1/32;
            }
            destination-port 80;
            protocol tcp;
        }
        then {
            accept;
            count sr31337;
        }
    }

With the following arguments to ``acl_script``::
    acl_script --modify-specific-term sr31337 --source-address 5.5.5.5 --replace-defined

The following is generated::

    term sr31337 {
        from {
            source-address {
                5.5.5.5/32;
            }
            destination-address {
                192.168.0.1/32;
            }
            destination-port 80;
            protocol tcp;
        }
        then {
            accept;
            count sr31337;
        }
    }

IOS-like
~~~~~~~~

More on this later!
