"""Parse and manipulate network access control lists.

This library doesn't completely follow the border of the valid/invalid ACL
set, which is determined by multiple vendors and not completely documented
by any of them.  We could asymptotically approach that with an enormous
amount of testing, although it would require a 'flavor' flag (vendor,
router model, software version) for full support.  The realistic goal
is to catch all the errors that we see in practice, and to accept all
the ACLs that we use in practice, rather than to try to reject *every*
invalid ACL and accept *every* valid ACL.

>>> from trigger.acl import parse
>>> aclobj = parse("access-list 123 permit tcp any host 10.20.30.40 eq 80")
>>> aclobj.terms
[<Term: None>]
"""

"""
7/15/2014
This file was split into smaller modules: dicts, grammar, junos, ios, and support.
These modules are then included back into parser.py.
This makes the code more readable.
"""

from simpleparse.common import comments, strings  # noqa: E402, F401
from simpleparse.dispatchprocessor import (  # noqa: E402
    DispatchProcessor,
    dispatch,
    dispatchList,
)
from simpleparse.parser import Parser  # noqa: E402

from trigger import exceptions  # noqa: E402

from .ios import *  # noqa: F403, E402
from .junos import *  # noqa: F403, E402
from .support import *  # noqa: F403, E402

# Exports
__all__ = (
    # Classes
    "ACL",  # noqa: F405
    "TIP",  # noqa: F405
    "ACLParser",
    "ACLProcessor",
    "Comment",  # noqa: F405
    "Matches",  # noqa: F405
    "Policer",  # noqa: F405
    "PolicerGroup",  # noqa: F405
    "Protocol",  # noqa: F405
    "RangeList",  # noqa: F405
    "Remark",  # noqa: F405
    "S",  # noqa: F405
    "Term",  # noqa: F405
    "TermList",  # noqa: F405
    # Functions
    "check_range",  # noqa: F405
    "default_processor",
    "do_port_lookup",  # noqa: F405
    "do_protocol_lookup",  # noqa: F405
    "literals",  # noqa: F405
    "make_nondefault_processor",
    "parse",
    # Constants,
    "ports",  # noqa: F405
    "strip_comments",  # noqa: F405
)

# Temporary resting place for comments, so the rest of the parser can
# ignore them.  Yes, this makes the library not thread-safe.
Comments = []

#
# Parsing infrastructure
#


class ACLProcessor(DispatchProcessor):
    """SimpleParse dispatch processor for ACL grammar rules."""


def default_processor(self, tag_info, buffer):  # noqa: D103
    _tag, start, stop, subtags = tag_info
    if not subtags:
        return buffer[start:stop]
    if len(subtags) == 1:
        return dispatch(self, subtags[0], buffer)
    return dispatchList(self, subtags, buffer)


def make_nondefault_processor(action):  # noqa: D103
    if callable(action):

        def processor(self, tag_info, buffer):
            tag, start, stop, subtags = tag_info
            if tag in subtagged:  # noqa: F405
                results = [
                    getattr(self, subtag[0])(subtag, buffer) for subtag in subtags
                ]
                return action(strip_comments(results))  # noqa: F405
            return action(buffer[start:stop])

    else:

        def processor(self, tag_info, buffer):
            return action

    return processor


grammar = []
for production, rule in rules.items():  # noqa: F405
    if isinstance(rule, tuple):
        assert len(rule) == 2  # noqa: S101, PLR2004
        setattr(ACLProcessor, production, make_nondefault_processor(rule[1]))
        grammar.append(f"{production} := {rule[0]}")
    else:
        setattr(ACLProcessor, production, default_processor)
        grammar.append(f"{production} := {rule}")

grammar = "\n".join(grammar)


class ACLParser(Parser):
    """SimpleParse parser for ACL text."""

    def buildProcessor(self):  # noqa: D102
        return ACLProcessor()


def parse(input_data):
    """Parse a complete ACL and return an ACL object. This should be the only
    external interface to the parser.

    >>> from trigger.acl import parse
    >>> aclobj = parse("access-list 123 permit tcp any host 10.20.30.40 eq 80")
    >>> aclobj.terms
    [<Term: None>]

    :param input_data:
        An ACL policy as a string or file-like object.
    """  # noqa: D205
    parser = ACLParser(grammar)

    try:
        data = input_data.read()
    except AttributeError:
        data = input_data

    ## parse the acl
    success, children, nextchar = parser.parse(data)

    if success and nextchar == len(data):
        assert len(children) == 1  # noqa: S101
        return children[0]
    line = data[:nextchar].count("\n") + 1
    column = len(data[data[nextchar].rfind("\n") : nextchar]) + 1
    msg = "Could not match syntax.  Please report as a bug."
    raise exceptions.ParseError(
        msg,
        line,
        column,
    )
