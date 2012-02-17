# -*- coding: utf-8 -*-

"""
All exceptions for trigger.acl. None of these have docstrings. We're working on
it!
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2010-2011, AOL Inc.'

from simpleparse.error import ParserSyntaxError

class ParseError(Exception):
    """Error parsing/normalizing an ACL that tries to tell you where it
    failed"""
    def __init__(self, reason, line=None, column=None):
        self.reason = reason
        self.line = line
        self.column = column

    def __str__(self):
        s = self.reason
        if self.line is not None and self.line > 1:
            s += ' at line %d' % self.line
        return s

class ACLError(Exception): pass

# ACL validation/formating errors
class BadTermNameError(ACLError): pass
class MissingTermNameError(ACLError): pass
class VendorSupportLackingError(ACLError): pass

# ACL naming errors
class ACLNameError(ACLError): pass
class MissingACLNameError(ACLNameError): pass
class BadACLNameError(ACLNameError): pass

# Misc. action errors
class ActionError(ACLError): pass
class UnknownActionNameError(ActionError): pass
class RoutingInstanceNameError(ActionError): pass
class RejectCodeError(ActionError): pass
class CounterNameError(ActionError): pass
class ForwardingClassNameError(ActionError): pass
class IPSecSANameError(ActionError): pass
class PolicerNameError(ActionError): pass

# Argument matching errors
class MatchError(ACLError): pass
class MatchArgRangeError(MatchError): pass
class UnknownMatchTypeError(MatchError): pass
class UnknownMatchArgError(MatchError): pass

# ACLs database errors
class ACLSetError(ACLError): pass
class ModifyACLSetError(ACLSetError): pass
class InvalidACLSetError(ACLSetError): pass
