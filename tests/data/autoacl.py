# Dummy version of autoacl.py, for test cases.

from twisted.python import log

DC_ONCALL_ID = "17"


def autoacl(dev, explicit_acls=None):
    """A simple test case. NYI"""
    acls = set()
    log.msg(f"[{dev}]: Adding auto ACLs")
    if dev.vendor == "juniper":
        log.msg(f"[{dev}]: Adding 115j")
        acls.add("115j")
        if dev.onCallID == DC_ONCALL_ID:
            acls.add("router-protect.core")
            log.msg(f"[{dev}]: Adding router-protect.core")
        else:
            acls.add("router-protect")
            log.msg(f"[{dev}]: Adding router-protect")

    return acls
