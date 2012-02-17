# Dummy version of autoacl.py, for test cases.

from sets import Set

ATDN_ONCALL = '80'

def autoacl(dev):
    acls = Set()
    if dev.manufacturer == 'JUNIPER':
	# Make sure that explicit_acls is already populated.
	assert '181j' in dev.explicit_acls

	acls.add('115j')
	if dev.onCallID == ATDN_ONCALL:
	    acls.add('protectRE.atdn')
	else:
	    acls.add('protectRE')
    return acls
