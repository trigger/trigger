#!/usr/bin/env python

"""autoacl.py - This file controls when ACLs get auto-applied to network devices,
in addition to what is explicitly specified in :class:`~trigger.acl.db.AclsDB`.

After editing this file, run ``python autoacl.py`` to make sure the
syntax is ok.  Several things will break if you break this file.

You can also run this with '-v' to output the list of all devices
and what ACLs will be applied to them.  You can save this output
before editing and compare it to the output after your change.

Skip down a bit to find the part you should edit.
"""  # noqa: D205

import sys

from twisted.python import log

from trigger.conf import settings

# Exports
__all__ = ("autoacl",)

# ===============================
# BEGIN USER-SERVICEABLE PARTS
# ===============================

log.msg("IN CUSTOM AUTOACL.PY FILE:", __file__)
OWNERS = settings.VALID_OWNERS


def autoacl(dev, explicit_acls=None):  # noqa: PLR0912
    """Given a NetDevice object, returns a set of **implicit** (auto) ACLs. We require
    a device object so that we don't have circular dependencies between netdevices
    and autoacl.

    This function MUST return a set() of acl names or you will break the ACL
    associations. An empty set is fine, but it must be a set!

    :param dev: A :class:`~trigger.netdevices.NetDevice` object.
    :param explicit_acls: A set containing names of ACLs. Default: set()

    >>> dev = nd.find('test1-abc')
    >>> dev.vendor
    <Vendor: Juniper>
    >>> autoacl(dev)
    set(['juniper-router-protect', 'juniper-router.policer'])
    """  # noqa: D205
    # Explicitly pass a set of explicit_acls so that we can use it as a
    # dependency for assigning implicit_acls. Defaults to an empty set.
    if explicit_acls is None:
        log.msg(f"[{dev}]: explicit_acls unset")
        explicit_acls = set()

    # Skip anything not owned by valid groups
    if dev.owningTeam not in OWNERS:
        log.msg(f"[{dev}]: invalid owningTeam")
        return set()

    # Skip firewall devices
    if dev.deviceType == "FIREWALL":
        log.msg(f"[{dev}]: firewall device")
        return set()

    # Prep acl set
    log.msg(f"[{dev}]: autoacls initialized")
    acls = set()

    #
    # ACL Magic starts here
    #
    if dev.vendor in ("brocade", "cisco", "foundry"):
        log.msg("[%s]: adding ACLs ('118', '119')")
        acls.add("118")
        acls.add("119")

    #
    # Other GSR acls
    #
    if dev.vendor == "cisco":
        log.msg(f"[{dev}]: adding ACLs ('117')")
        acls.add("117")
        if (
            dev.make == "12000 SERIES" and dev.nodeName.startswith("pop")
        ) or dev.nodeName.startswith("bb"):
            log.msg(f"[{dev}]: adding ACLs ('backbone-acl')")
            acls.add("backbone-acl")
        elif dev.make == "12000 SERIES":
            log.msg(f"[{dev}]: adding ACLs ('gsr-acl')")
            acls.add("gsr-acl")
    #
    # Juniper acls
    #
    if dev.vendor == "juniper":
        if dev.deviceType == "SWITCH":
            log.msg(f"[{dev}]: adding ACLs ('juniper-switch-protect')")
            acls.add("juniper-switch-protect")
        else:
            log.msg(f"[{dev}]: adding ACLs ('juniper-router-protect')")
            acls.add("juniper-router-protect")
            acls.add("juniper-router.policer")

    #
    # Explicit ACL example
    #
    # Only add acl '10' (or variants) to the device if 'acb123.special' is not
    # explicitly associated with the device.
    if "10.special" in explicit_acls:
        pass
    elif dev.deviceType == "ROUTER":
        log.msg(f"[{dev}]: adding ACLs ('10')")
        acls.add("10")
    elif dev.deviceType == "SWITCH":
        log.msg(f"[{dev}]: adding ACLs ('10.sw')")
        acls.add("10.sw")

    return acls


# ===============================
# END USER-SERVICEABLE PARTS
# ===============================


def main():
    """A simple syntax check and dump of all we see and know!"""  # noqa: D401
    print("Syntax ok.")
    if len(sys.argv) > 1:
        from trigger.netdevices import NetDevices

        nd = NetDevices()
        names = sorted(nd)
        for name in names:
            dev = nd[name]
            if dev.deviceType not in ("ROUTER", "SWITCH"):
                continue
            acls = sorted(dev.acls)
            print(f"{name:<39} {' '.join(acls)}")


if __name__ == "__main__":
    main()
