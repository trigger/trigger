=================================
check_access - ACL Access Checker
=================================

.. contents::
    :local:
    :depth: 2

About
=====

**check_access** determines if access is already in an ACL and if not provides
the output to add.

Usage
=====

Here is the usage signature::

    Usage: check_access [opts] file source dest [protocol [port]]

Examples
========

Let's start with a simple Cisco extended ACL called ``acl.abc123`` that looks
like this::

    % cat acl.abc123
    no ip access-list extended abc123
    ip access-list extended abc123
    !
    !!! Permit this network
    permit tcp 10.17.18.0 0.0.0.31 any
    !
    !!! Default deny
    deny ip any any

Let's use the example flow of checking whether http (port 80/tcp) is permitted from
any source to the destination ``10.20.30.40`` in the policy ``acl.abc123``::

    % check_access acl.abc123 any 10.20.30.40 tcp 80
    !
    !!! Permit this network
    permit tcp 10.17.18.0 0.0.0.31 any
    ! check_access: ADD THIS TERM
    permit tcp any host 10.20.30.40 eq 80
    !
    !!! Default deny
    deny ip any any

It adds a comment that says ``"check_access: ADD THIS TERM"``, followed by the
policy one would need to add, and where (above the explicit deny).

Now if it were permitted, say if we chose ``10.17.18.19`` as the source, it
would tell you something different::

    % check_access acl.acb123 10.17.18.19 10.20.30.40 tcp 80
    !
    !!! Permit this network
    !  check_access: PERMITTED HERE
    permit tcp 10.17.18.0 0.0.0.31 any
    !
    !!! Default deny
    deny ip any any
    No edits needed.

It adds a comment that says ``"check_access: PERMITTED HERE"``, followed by the
policy that matches the flow. Additionally at the end it also reports ``"No edits needed"``.
