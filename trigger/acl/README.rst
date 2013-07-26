acl
===

Network access control list parsing library.

This is being forked from the ACL lib that is bundled with `Trigger
<https://github.com/trigger/trigger>`_. The goal is to pull this out of Trigger and
have it be a stand-alone project. Once it becomes stable, it will be pulled out
of Trigger core and converted into an optional feature.

Parsing Access-lists
~~~~~~~~~~~~~~~~~~~~

Let's start with a simple Cisco ACL::

    >>> from trigger.acl import parse
    >>> aclobj = parse("access-list 123 permit tcp any host 10.20.30.40 eq 80")
    >>> aclobj.terms
    [<Term: None>]
    >>> t = aclobj.terms[0]
    >>> t.match
    <Matches: destination-port [80], destination-address [IP('10.20.30.40')],
              protocol [<Protocol: tcp>]>

And convert it to Juniper format::

    >>> aclobj.name_terms() # Juniper policy terms must have names
    >>> aclobj.terms
    [<Term: T1>]
    >>> print '\n'.join(aclobj.output(format='junos'))
    filter 123 {
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
            }
        }
    }


Checking Access
~~~~~~~~~~~~~~~

Coming Soon(TM).

Noteworthy
~~~~~~~~~~

DSCP:
Juniper does not allow the inclusion of 'dscp' and 'dscp-except' in the same term.  The latter will override any others.

Observe::

    me@router# load merge terminal
    [Type ^D at a new line to end input]
    firewall filter asdf {
        term DSCP_term {
            /* Project:"non-zero TOS value DCSP" */
            from {
                dscp-except [ af11 cs0 ];
                dscp [ af11 be cs0 cs7 ];
            }
            then {
                count match_non_zero_DCSP;
                port-mirror;
                next term;
            }
        }
    }
    load complete

    [edit]
    me@router# show firewall filter asdf
    term DSCP_term {
        /* Project:"non-zero TOS value DCSP" */
        from {
            dscp [ af11 be cs0 cs7 ];
        }
        then {
            count match_non_zero_DCSP;
            port-mirror;
            next term;
        }
    }

    [edit]
    me@router#

