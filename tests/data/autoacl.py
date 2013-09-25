# Dummy version of autoacl.py, for test cases.

from twisted.python import log

DC_ONCALL_ID = '17'

def autoacl(dev, explicit_acls=None):
    """A simple test case. NYI"""
    acls = set()
    log.msg('[%s]: Adding auto ACLs' % dev)
    if dev.vendor == 'juniper':
        log.msg('[%s]: Adding 115j' % dev)
        acls.add('115j')
        if dev.onCallID == DC_ONCALL_ID:
            acls.add('router-protect.core')
            log.msg('[%s]: Adding router-protect.core' % dev)
        else:
            acls.add('router-protect')
            log.msg('[%s]: Adding router-protect' % dev)

    return acls
