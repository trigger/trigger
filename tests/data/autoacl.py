# Dummy version of autoacl.py, for test cases.

DC_ONCALL_ID = '17'

def autoacl(dev, explicit_acls=None):
    """return a bare set"""
    acls = set()

    return acls

# TODO (jathan): Update the acls.db tests to pickup what we define here
def _autoacl(dev, explicit_acls=None):
    """A simple test case. NYI"""
    if dev.vendor == 'juniper':
        acls.add('115j')
        if dev.onCallID == DC_ONCALL_ID:
            acls.add('router-protect.core')
        else:
            acls.add('router-protect')

    return acls
