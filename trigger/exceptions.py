# -*- coding: utf-8 -*-

"""
All custom exceptions used by Trigger. Where possible built-in exceptions are
used, but sometimes we need more descriptive errors.
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan@gmail.com'
__copyright__ = 'Copyright 2012-2012, AOL Inc.'
__version__ = '1.9'


# Imports
from simpleparse.error import ParserSyntaxError


# Exceptions
class TriggerError(Exception):
    """A base exception for all Trigger-related errors."""


class ImproperlyConfigured(TriggerError):
    """Raised when something is improperly... configured..."""


################
# ACL Exceptions
################
class ACLError(TriggerError):
    """Base exception for all ACL-related errors."""


class ParseError(ACLError):
    """
    Raised when there is an error parsing/normalizing an ACL that tries to tell
    you where it failed.
    """
    def __init__(self, reason, line=None, column=None):
        self.reason = reason
        self.line = line
        self.column = column

    def __str__(self):
        s = self.reason
        if self.line is not None and self.line > 1:
            s += ' at line %d' % self.line
        return s


# ACL validation/formating errors
class BadTermName(ACLError):
    """
    Raised when an invalid name is assigned to a `~trigger.acl.parser.Term`
    object
    """


class MissingTermName(ACLError):
    """
    Raised when a an un-named Term is output to a format that requires Terms to
    be named (e.g. Juniper).
    """


class VendorSupportLacking(ACLError):
    """Raised when a feature is not supported by a given vendor."""


# ACL naming errors
class ACLNameError(ACLError):
    """A base exception for all ACL naming errors."""


class MissingACLName(ACLNameError):
    """Raised when an ACL object is missing a name."""


class BadACLName(ACLNameError):
    """Raised when an ACL object is assigned an invalid name."""


# Misc. action errors
class ActionError(ACLError):
    """A base exception for all `~trigger.acl.parser.Term` action errors."""


class UnknownActionName(ActionError):
    """
    Raised when an action assigned to a ~trigger.acl.parser.Term` object is
    unknown.
    """


class BadRoutingInstanceName(ActionError):
    """
    Raised when a routing-instance name specified in an action is invalid.
    """


class BadRejectCode(ActionError):
    """Raised when an invalid rejection code is specified."""


class BadCounterName(ActionError):
    """Raised when a counter name is invalid."""


class BadForwardingClassName(ActionError):
    """Raised when a forwarding-class name is invalid."""


class BadIPSecSAName(ActionError):
    """Raised when an IPSec SA name is invalid."""


class BadPolicerName(ActionError):
    """Raised when a policer name is invalid."""


# Argument matching errors
class MatchError(ACLError):
    """
    A base exception for all errors related to Term
    `~trigger.acl.parser.Matches` objects.
    """


class BadMatchArgRange(MatchError):
    """
    Raised when a match condition argument does not fall within a specified
    range.
    """


class UnknownMatchType(MatchError):
    """Raised when an unknown match condition is specified."""


class UnknownMatchArg(MatchError):
    """Raised when an unknown match argument is specified."""


# ACLs database errors
class ACLSetError(ACLError):
    """A base exception for all ACL Set errors."""


class InvalidACLSet(ACLSetError):
    """Raised when an invalid ACL set is specified."""


# ACL/task queue errors
class ACLQueueError(TriggerError):
    """Raised when we encounter errors communicating with the Queue."""


# ACL workflow errors
class ACLStagingFailed(ACLError):
    """Raised when we encounter errors staging a file for loading."""


######################
# NetScreen Exceptions
######################
class NetScreenError(TriggerError):
    """A general exception for NetScreen devices."""


class NetScreenParseError(NetScreenError):
    """Raised when a NetScreen policy cannot be parsed."""


#####################
# Commando Exceptions
#####################
class CommandoError(TriggerError):
    """A base exception for all Commando-related errors."""


class UnsupportedVendor(CommandoError):
    """Raised when a vendor is not supported by Trigger."""


class UnsupportedDeviceType(CommandoError):
    """Raised when a device type is not supported by Trigger."""


class MissingPlatform(CommandoError):
    """Raised when a specific device platform is not supported."""


####################
# Twister Exceptions
####################
class TwisterError(TriggerError):
    """A base exception for all errors related to Twister."""


class LoginFailure(TwisterError):
    """Raised when authentication to a remote system fails."""


class EnablePasswordFailure(LoginFailure):
    """Raised when enable password was required but not found."""


class LoginTimeout(LoginFailure):
    """Raised when login to a remote systems times out."""


class ConnectionFailure(TwisterError):
    """Raised when a connection attempt totally fails."""


class SSHConnectionLost(TwisterError):
    """Raised when an SSH connection is lost for any reason."""
    def __init__(self, code, desc):
        self.code = code
        TwisterError.__init__(self, desc)


class CommandTimeout(TwisterError):
    """Raised when a command times out while executing."""


class CommandFailure(TwisterError):
    """
    Raised when a command fails to execute, such as when it results in an
    error.
    """


class IoslikeCommandFailure(CommandFailure):
    """Raised when a command fails on an IOS-like device."""


class NetscalerCommandFailure(CommandFailure):
    """Raised when a command fails on a NetScaler device."""


class JunoscriptCommandFailure(CommandFailure):
    """Raised when a Junoscript command fails on a Juniper device."""
    def __init__(self, tag):
        self.tag = tag

    def __str__(self):
        s = 'JunOS XML command failure:\n'
        ns = '{http://xml.juniper.net/xnm/1.1/xnm}'
        for e in self.tag.findall('.//%serror' % ns):
            for e2 in e:
                s += '  %s: %s\n' % (e2.tag.replace(ns, ''), e2.text)
        return s


#######################
# NetDevices Exceptions
#######################
class NetDeviceError(TriggerError):
    """A base exception for all NetDevices related errors."""


class BadVendorName(NetDeviceError):
    """Raised when a Vendor object has a problem with the name."""


class LoaderFailed(NetDeviceError):
    """Raised when a metadata loader failed to load from data source."""


#########################
# Notification Exceptions
#########################
class NotificationFailure(TriggerError):
    """Raised when a notification fails and has not been silenced."""


##############################
# Bounce/Changemgmt Exceptions
##############################
class InvalidBounceWindow(TriggerError):
    """Raised when a BounceWindow object is kind of not good."""


#####################
# TACACSrc Exceptions
#####################
class TacacsrcError(Exception):
    """Base exception for TACACSrc errors."""


class CouldNotParse(TacacsrcError):
    """Raised when a ``.tacacsrc`` file failed to parse."""


class MissingPassword(TacacsrcError):
    """Raised when a credential is missing a password."""


class MissingRealmName(TacacsrcError):
    """Raised when a credential is missing a realm."""


class VersionMismatch(TacacsrcError):
    """Raised when the TACACSrc version does not match."""
