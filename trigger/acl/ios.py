"""Originally from parser.py. Not meant to be used by itself.
For IOS like ACLs.

#Constants
    unary_port_operators
    rules - this is really from the grammar.py
# Classes
    'Remark',
# Functions
    'handle_ios_match',
    'handle_ios_acl',
"""  # noqa: D205

from .grammar import *  # noqa: F403


class Remark(Comment):  # noqa: F405
    """IOS extended ACL "remark" lines automatically become comments when
    converting to other formats of ACL.
    """  # noqa: D205

    def output_ios_named(self):
        """Output the Remark to IOS named format."""
        return " remark " + self.data


# Build a table to unwind Cisco's weird inverse netmask.
# TODO (jathan): These don't actually get sorted properly, but it doesn't seem
# to have mattered up until now. Worth looking into it at some point, though.
inverse_mask_table = dict([(make_inverse_mask(x), x) for x in range(33)])  # noqa: F405


def handle_ios_match(a):  # noqa: D103, PLR0912
    protocol, source, dest = a[:3]
    extra = a[3:]

    match = Matches()  # noqa: F405
    modifiers = Modifiers()  # noqa: F405

    if protocol:
        match["protocol"] = [protocol]

    for sd, arg in (("source", source), ("destination", dest)):
        if isinstance(arg, list):
            if arg[0] is not None:
                match[sd + "-address"] = [arg[0]]
            match[sd + "-port"] = arg[1]
        elif arg is not None:
            match[sd + "-address"] = [arg]

    if "log" in extra:
        modifiers["syslog"] = True
        extra.remove("log")

    if protocol == "icmp":
        if len(extra) > 2:  # noqa: PLR2004
            raise NotImplementedError(extra)
        if extra and isinstance(extra[0], tuple):
            extra = extra[0]
        if len(extra) >= 1:
            match["icmp-type"] = [extra[0]]
        if len(extra) >= 2:  # noqa: PLR2004
            match["icmp-code"] = [extra[1]]
    elif protocol == "tcp":
        if extra == ["established"]:
            match["tcp-flags"] = [tcp_flag_specials["tcp-established"]]  # noqa: F405
        elif extra:
            raise NotImplementedError(extra)
    elif extra:
        raise NotImplementedError(extra)

    return {"match": match, "modifiers": modifiers}


def handle_ios_acl(rows):  # noqa: D103, PLR0912
    acl = ACL()  # noqa: F405
    for d in rows:
        if not d:
            continue
        for k, v in d.items():
            if k == "no":
                acl = ACL()  # noqa: F405
            elif k == "name":
                if acl.name:
                    if v != acl.name:
                        msg = f"Name '{v}' does not match ACL '{acl.name}'"
                        raise exceptions.ACLNameError(  # noqa: F405
                            msg,
                        )
                else:
                    acl.name = v
            elif k == "term":
                acl.terms.append(v)
            elif k == "format":
                acl.format = v
            # Brocade receive-acl
            elif k == "receive_acl":
                acl.is_receive_acl = True
            else:
                msg = f'unknown key "{k}" (value {v})'
                raise RuntimeError(msg)
    # In traditional ACLs, comments that belong to the first ACE are
    # indistinguishable from comments that belong to the ACL.
    # if acl.format == 'ios' and acl.terms:
    if acl.format in ("ios", "ios_brocade") and acl.terms:
        acl.comments += acl.terms[0].comments
        acl.terms[0].comments = []
    return acl


unary_port_operators = {
    "eq": lambda x: [x],
    "le": lambda x: [(0, x)],
    "lt": lambda x: [(0, x - 1)],
    "ge": lambda x: [(x, 65535)],
    "gt": lambda x: [(x + 1, 65535)],
    "neq": lambda x: [(0, x - 1), (x + 1, 65535)],
}

rules.update(  # noqa: F405
    {
        "ios_ip": "kw_any / host_ipv4 / ios_masked_ipv4",
        "kw_any": ('"any"', None),
        "host_ipv4": '"host", ts, ipv4',
        S("ios_masked_ipv4"): (  # noqa: F405
            "ipv4, ts, ipv4_inverse_mask",
            # Python 3: Explicit tuple unpacking for string formatting
            lambda x: TIP("%s/%d" % (x[0], x[1])),  # noqa: UP031, F405
        ),
        "ipv4_inverse_mask": (
            literals(inverse_mask_table),  # noqa: F405
            lambda x: inverse_mask_table[TIP(x)],  # noqa: F405
        ),
        "kw_ip": ('"ip"', None),
        S("ios_match"): (  # noqa: F405
            "kw_ip / protocol, ts, ios_ip, ts, ios_ip, (ts, ios_log)?",
            handle_ios_match,
        ),
        S("ios_tcp_port_match"): (  # noqa: F405
            "tcp, ts, ios_ip_port, ts, ios_ip_port, (ts, established)?, (ts, ios_log)?",
            handle_ios_match,
        ),
        S("ios_udp_port_match"): (  # noqa: F405
            "udp, ts, ios_ip_port, ts, ios_ip_port, (ts, ios_log)?",
            handle_ios_match,
        ),
        S("ios_ip_port"): "ios_ip, (ts, unary_port / ios_range)?",  # noqa: F405
        S("unary_port"): (  # noqa: F405
            "unary_port_operator, ts, port",
            lambda x: unary_port_operators[x[0]](x[1]),
        ),
        "unary_port_operator": literals(unary_port_operators),  # noqa: F405
        S("ios_range"): ('"range", ts, port, ts, port', lambda xy: [(xy[0], xy[1])]),  # noqa: F405
        "established": '"established"',
        S("ios_icmp_match"): (  # noqa: F405
            "icmp, ts, ios_ip, ts, ios_ip, (ts, ios_log)?, "
            "(ts, ios_icmp_message / "
            " (icmp_type, (ts, icmp_code)?))?, (ts, ios_log)?",
            handle_ios_match,
        ),
        "ios_icmp_message": (
            literals(ios_icmp_messages),  # noqa: F405
            lambda x: ios_icmp_messages[x],  # noqa: F405
        ),
        "ios_action": '"permit" / "deny"',
        "ios_log": '"log-input" / "log"',
        S("ios_action_match"): (  # noqa: F405
            "ios_action, ts, ios_tcp_port_match / "
            "ios_udp_port_match / ios_icmp_match / ios_match",
            lambda x: {"term": Term(action=x[0], **x[1])},  # noqa: F405
        ),
        "ios_acl_line": "ios_acl_match_line / ios_acl_no_line",
        S("ios_acl_match_line"): (  # noqa: F405
            '"access-list", ts, digits, ts, ios_action_match',
            lambda x: update(x[1], name=x[0], format="ios"),  # noqa: F405
        ),
        S("ios_acl_no_line"): (  # noqa: F405
            '"no", ts, "access-list", ts, digits',
            lambda x: {"no": True, "name": x[0]},
        ),
        "ios_ext_line": (
            "ios_action_match / ios_ext_name_line / "
            "ios_ext_no_line / ios_remark_line / "
            "ios_rebind_acl_line / ios_rebind_receive_acl_line"
        ),
        S("ios_ext_name_line"): (  # noqa: F405
            '"ip", ts, "access-list", ts, "extended", ts, word',
            lambda x: {"name": x[0], "format": "ios_named"},
        ),
        S("ios_ext_no_line"): (  # noqa: F405
            '"no", ts, "ip", ts, "access-list", ts, "extended", ts, word',
            lambda x: {"no": True, "name": x[0]},
        ),
        # Brocade "ip rebind-acl foo" or "ip rebind-receive-acl foo" syntax
        S("ios_rebind_acl_line"): (  # noqa: F405
            '"ip", ts, "rebind-acl", ts, word',
            lambda x: {"name": x[0], "format": "ios_brocade"},
        ),
        # Brocade "ip rebind-acl foo" or "ip rebind-receive-acl foo" syntax
        S("ios_rebind_receive_acl_line"): (  # noqa: F405
            '"ip", ts, "rebind-receive-acl", ts, word',
            lambda x: {"name": x[0], "format": "ios_brocade", "receive_acl": True},
        ),
        S("icomment"): ('"!", ts?, icomment_body', lambda x: x),  # noqa: F405
        "icomment_body": ('-"\n"*', Comment),  # noqa: F405
        S("ios_remark_line"): (  # noqa: F405
            '("access-list", ts, digits_s, ts)?, "remark", ts, remark_body',
            lambda x: x,
        ),
        "remark_body": ('-"\n"*', Remark),
        ">ios_line<": ('ts?, (ios_acl_line / ios_ext_line / "end")?, ts?, icomment?'),
        S("ios_acl"): ('(ios_line, "\n")*, ios_line', handle_ios_acl),  # noqa: F405
    },
)
