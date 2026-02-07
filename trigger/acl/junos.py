"""Originally from parser.py. Not meant to be used by itself.
For JunOS like ACLs.

#Constants
    junos_match_types
    rules - this is really from the grammar.py
# Classes
    Policer
    PolicerGroup
    QuotedString
# Functions
    braced_list
    keyword_match
    range_match
    handle_junos_acl
    handle_junos_family_acl
    handle_junos_policers
    handle_junos_term
    juniper_multiline_comments
"""  # noqa: D205

from trigger.conf import settings

from .grammar import *  # noqa: F403

# Temporary resting place for comments, so the rest of the parser can
# ignore them.  Yes, this makes the library not thread-safe.
Comments = []


class Policer:
    """Container class for policer policy definitions. This is a dummy class for
    now, that just passes it through as a string.
    """  # noqa: D205

    def __init__(self, name, data):  # noqa: PLR0912, D107
        if not name:
            msg = "Policer requres name"
            raise exceptions.ActionError(msg)  # noqa: F405
        self.name = name
        self.exceedings = []
        self.actions = []
        for elt in data:
            for k, v in elt.items():
                if k == "if-exceeding":
                    for entry in v:
                        type, value = entry
                        if type == "bandwidth-limit":
                            limit = self.str2bits(value)
                            if limit > 32000000000 or limit < 32000:  # noqa: PLR2004
                                msg = "bandwidth-limit must be between 32000bps and 32000000000bps"
                                raise ValueError(msg)
                            self.exceedings.append((type, limit))
                        elif type == "burst-size-limit":
                            limit = self.str2bits(value)
                            if limit > 100000000 or limit < 1500:  # noqa: PLR2004
                                msg = "burst-size-limit must be between 1500B and 100,000,000B"
                                raise ValueError(msg)
                            self.exceedings.append((type, limit))
                        elif type == "bandwidth-percent":
                            limit = int(value)
                            if limit < 1 or limit > 100:  # noqa: PLR2004
                                msg = "bandwidth-percent must be between 1 and 100"
                                raise ValueError(msg)
                        else:
                            msg = f"Unknown policer if-exceeding tag: {type}"
                            raise ValueError(msg)
                elif k == "action":
                    for i in v:
                        self.actions.append(i)

    def str2bits(self, str):  # noqa: D102
        try:
            val = int(str)
        except Exception as err:
            if str[-1] == "k":
                return int(str[0:-1]) * 1024
            if str[-1] == "m":
                return int(str[0:-1]) * 1048576
            msg = f"invalid bit definition {str}"
            raise ValueError(msg) from err
        return val

    def __repr__(self):  # noqa: D105
        return f"<{self.__class__.__name__}: {self.name!r}>"

    def __str__(self):  # noqa: D105
        return self.data

    def output(self):  # noqa: D102
        output = [f"policer {self.name} {{"]
        if self.exceedings:
            output.append("    if-exceeding {")
            output.extend(f"        {x[0]} {x[1]};" for x in self.exceedings)
            output.append("    }")
        if self.actions:
            output.append("    then {")
            output.extend(f"        {x};" for x in self.actions)

        if self.actions:
            output.append("    }")
        output.append("}")
        return output


class PolicerGroup:
    """Container for Policer objects. Juniper only."""

    def __init__(self, format=None):  # noqa: D107
        self.policers = []
        self.format = format
        global Comments  # noqa: PLW0603
        self.comments = Comments
        Comments = []

    def output(self, format=None, *largs, **kwargs):  # noqa: D102
        if format is None:
            format = self.format
        return getattr(self, "output_" + format)(*largs, **kwargs)

    def output_junos(self, replace=False):  # noqa: D102
        output = []
        for ent in self.policers:
            output.extend(ent.output())

        if replace:
            return ["firewall {", "replace:"] + ["    " + x for x in output] + ["}"]
        return output


class QuotedString(str):
    """String subclass that wraps its value in double quotes."""

    def __str__(self):  # noqa: D105
        return '"' + self + '"'


junos_match_types = []


def braced_list(arg):
    """Returned braced output.  Will alert if comment is malformed."""  # noqa: D401
    return '("{{", jws?, ({}, jws?)*, "}}"!{})'.format(arg, errs["comm_start"])  # noqa: F405


def keyword_match(keyword, arg=None):  # noqa: D103
    for k in keyword, keyword + "-except":
        prod = "junos_" + k.replace("-", "_")
        junos_match_types.append(prod)
        if arg is None:
            rules[prod] = (f'"{k}", jsemi', {k: True})  # noqa: F405
        else:
            tokens = f'"{k}", jws, '
            if k in address_matches:  # noqa: F405
                tokens += braced_list(arg + ", jsemi")
            else:
                tokens += arg + ", jsemi"
            rules[S(prod)] = (tokens, lambda x, k=k: {k: x})  # noqa: F405


keyword_match("address", "cidr / ipaddr")
keyword_match("destination-address", "cidr / ipaddr")
keyword_match("destination-prefix-list", "jword")
keyword_match("first-fragment")
keyword_match("fragment-flags", "fragment_flag")
keyword_match("ip-options", "ip_option")
keyword_match("is-fragment")
keyword_match("prefix-list", "jword")
keyword_match("source-address", "cidr / ipaddr")
keyword_match("source-prefix-list", "jword")
keyword_match("tcp-established")
keyword_match("tcp-flags", "tcp_flag")
keyword_match("tcp-initial")


def range_match(key, arg):  # noqa: D103
    rules[S(arg + "_range")] = (f'{arg}, "-", {arg}', tuple)  # noqa: F405
    match = f"{arg}_range / {arg}"
    keyword_match(key, f'{match} / ("[", jws?, ({match}, jws?)*, "]")')


range_match("ah-spi", "alphanums")
range_match("destination-mac-address", "macaddr")
range_match("destination-port", "port")
range_match("dscp", "dscp")
range_match("ether-type", "alphanums")
range_match("esp-spi", "alphanums")
range_match("forwarding-class", "jword")
range_match("fragment-offset", "port")
range_match("icmp-code", "icmp_code")
range_match("icmp-type", "icmp_type")
range_match("interface-group", "digits")
range_match("packet-length", "digits")
range_match("port", "port")
range_match("precedence", "jword")
range_match("protocol", "protocol")
range_match("source-mac-address", "macaddr")
range_match("source-port", "port")
range_match("vlan-ether-type", "alphanums")


def handle_junos_acl(x):
    """Parse JUNOS ACL and return an ACL object populated with Term and Policer
    objects.

    It's expected that x is a 2-tuple of (name, terms) returned from the
    parser.

    Don't forget to wrap your token in S()!
    """  # noqa: D205
    a = ACL(name=x[0], format="junos")  # noqa: F405
    for elt in x[1:]:
        # Handle dictionary args we throw at the constructor
        if isinstance(elt, dict):
            a.__dict__.update(elt)
        elif isinstance(elt, Term):  # noqa: F405
            a.terms.append(elt)
        elif isinstance(elt, Policer):
            a.policers.append(elt)
        else:
            msg = f"Bad Object: {elt!r}"
            raise RuntimeError(msg)
    return a


def handle_junos_family_acl(x):
    """Parses a JUNOS acl that contains family information and sets the family
    attribute for the ACL object.

    It's expected that x is a 2-tuple of (family, aclobj) returned from the
    parser.

    Don't forget to wrap your token in S()!
    """  # noqa: D401, D205
    family, aclobj = x
    aclobj.family = family
    return aclobj


def handle_junos_policers(x):
    """Parse JUNOS policers and return a PolicerGroup object."""
    p = PolicerGroup(format="junos")
    for elt in x:
        if isinstance(elt, Policer):
            p.policers.append(elt)
        else:
            msg = f"bad object: {elt!r} in policer"
            raise RuntimeError(msg)
    return p


def handle_junos_term(d):
    """Parse a JUNOS term and return a Term object."""
    if "modifiers" in d:
        d["modifiers"] = Modifiers(d["modifiers"])  # noqa: F405
    return Term(**d)  # noqa: F405


# For multiline comments
def juniper_multiline_comments():
    """Return appropriate multi-line comment grammar for Juniper ACLs.

    This depends on ``settings.ALLOW_JUNIPER_MULTLIINE_COMMENTS``.
    """
    single = '-("*/" / "\n")*'  # single-line comments only
    multi = '-"*/"*'  # syntactically correct multi-line support
    if settings.ALLOW_JUNIPER_MULTILINE_COMMENTS:
        return multi
    return single


rules.update(  # noqa: F405
    {
        "jword": "double_quoted / word",
        "double_quoted": ('"\\"", -[\\"]+, "\\""', lambda x: QuotedString(x[1:-1])),
        ">jws<": "(ws / jcomment)+",
        S("jcomment"): ("jslashbang_comment", lambda x: Comment(x[0])),  # noqa: F405
        "<comment_start>": '"/*"',
        "<comment_stop>": '"*/"',
        ">jslashbang_comment<": "comment_start, jcomment_body, !{}, comment_stop".format(
            errs["comm_stop"],  # noqa: F405
        ),
        "jcomment_body": juniper_multiline_comments(),
        # Errors on missing ';', ignores multiple ;; and normalizes to one.
        "<jsemi>": "jws?, [;]+!{}".format(errs["semicolon"]),  # noqa: F405
        "fragment_flag": literals(fragment_flag_names),  # noqa: F405
        "ip_option": "digits / " + literals(ip_option_names),  # noqa: F405
        "tcp_flag": literals(tcp_flag_names),  # noqa: F405
    },
)

# Note there cannot be jws (including comments) before or after the "filter"
# section of the config.  It's wrong to do this anyway, since if you load
# that config onto the router, the comments will not remain in place on
# the next load of a similar config (e.g., another ACL).  I had a workaround
# for this but it made the parser substantially slower.
rules.update(  # noqa: F405
    {
        S("junos_raw_acl"): (  # noqa: F405
            'jws?, "filter", jws, jword, jws?, '
            + braced_list("junos_iface_specific / junos_term / junos_policer"),
            handle_junos_acl,
        ),
        "junos_iface_specific": (
            '("interface-specific", jsemi)',
            lambda x: {"interface_specific": len(x) > 0},
        ),
        "junos_replace_acl": (
            'jws?, "firewall", jws?, "{", jws?, "replace:", jws?, (junos_raw_acl, jws?)*, "}"'
        ),
        S("junos_replace_family_acl"): (  # noqa: F405
            'jws?, "firewall", jws?, "{", jws?, junos_filter_family, jws?, "{", jws?, "replace:", jws?, (junos_raw_acl, jws?)*, "}", jws?, "}"',
            handle_junos_family_acl,
        ),
        S("junos_replace_policers"): (  # noqa: F405
            '"firewall", jws?, "{", jws?, "replace:", jws?, (junos_policer, jws?)*, "}"',
            handle_junos_policers,
        ),
        "junos_filter_family": ('"family", ws, junos_family_type'),
        "junos_family_type": ('"inet" / "inet6" / "ethernet-switching"'),
        "opaque_braced_group": (
            '"{", jws?, (jword / "[" / "]" / ";" / opaque_braced_group / jws)*, "}"',
            lambda x: x,
        ),
        S("junos_term"): (  # noqa: F405
            'maybe_inactive, "term", jws, junos_term_name, '
            "jws?, " + braced_list("junos_from / junos_then"),
            lambda x: handle_junos_term(dict_sum(x)),  # noqa: F405
        ),
        S("junos_term_name"): ("jword", lambda x: {"name": x[0]}),  # noqa: F405
        "maybe_inactive": ('("inactive:", jws)?', lambda x: {"inactive": len(x) > 0}),
        S("junos_from"): (  # noqa: F405
            '"from", jws?, ' + braced_list("junos_match"),
            lambda x: {"match": Matches(dict_sum(x))},  # noqa: F405
        ),
        S("junos_then"): ("junos_basic_then / junos_braced_then", dict_sum),  # noqa: F405
        S("junos_braced_then"): (  # noqa: F405
            '"then", jws?, ' + braced_list("junos_action/junos_modifier, jsemi"),
            dict_sum,  # noqa: F405
        ),
        S("junos_basic_then"): ('"then", jws?, junos_action, jsemi', dict_sum),  # noqa: F405
        S("junos_policer"): (  # noqa: F405
            '"policer", jws, junos_term_name, jws?, '
            + braced_list("junos_exceeding / junos_policer_then"),
            lambda x: Policer(x[0]["name"], x[1:]),
        ),
        S("junos_policer_then"): (  # noqa: F405
            '"then", jws?, ' + braced_list("junos_policer_action, jsemi")
        ),
        S("junos_policer_action"): (  # noqa: F405
            'junos_discard / junos_fwd_class / ("loss-priority", jws, jword)',
            lambda x: {"action": x},
        ),
        "junos_discard": ('"discard"'),
        "junos_loss_pri": (
            '"loss-priority", jws, jword',
            lambda x: {"loss-priority": x[0]},
        ),
        "junos_fwd_class": (
            '"forwarding-class", jws, jword',
            lambda x: {"forwarding-class": x[0]},
        ),
        "junos_filter_specific": ('"filter-specific"'),
        S("junos_exceeding"): (  # noqa: F405
            '"if-exceeding", jws?, '
            + braced_list("junos_bw_limit/junos_bw_perc/junos_burst_limit"),
            lambda x: {"if-exceeding": x},
        ),
        S("junos_bw_limit"): (  # noqa: F405
            '"bandwidth-limit", jws, word, jsemi',
            lambda x: ("bandwidth-limit", x[0]),
        ),
        S("junos_bw_perc"): (  # noqa: F405
            '"bandwidth-percent", jws, alphanums, jsemi',
            lambda x: ("bandwidth-percent", x[0]),
        ),
        S("junos_burst_limit"): (  # noqa: F405
            '"burst-size-limit", jws, alphanums, jsemi',
            lambda x: ("burst-size-limit", x[0]),
        ),
        S("junos_match"): (" / ".join(junos_match_types), dict_sum),  # noqa: F405
        S("junos_action"): (  # noqa: F405
            "junos_one_action / junos_reject_action /"
            "junos_reject_action / junos_ri_action",
            lambda x: {"action": x[0]},
        ),
        "junos_one_action": ('"accept" / "discard" / "reject" / ("next", jws, "term")'),
        "junos_reject_action": (
            '"reject", jws, ' + literals(icmp_reject_codes),  # noqa: F405
            lambda x: ("reject", x),
        ),
        S("junos_ri_action"): (  # noqa: F405
            '"routing-instance", jws, jword',
            lambda x: ("routing-instance", x[0]),
        ),
        S("junos_modifier"): (  # noqa: F405
            "junos_one_modifier / junos_arg_modifier",
            lambda x: {"modifiers": x},
        ),
        "junos_one_modifier": (
            '"log" / "sample" / "syslog" / "port-mirror"',
            lambda x: (x, True),
        ),
        S("junos_arg_modifier"): "junos_arg_modifier_kw, jws, jword",  # noqa: F405
        "junos_arg_modifier_kw": (
            '"count" / "forwarding-class" / "ipsec-sa" /"loss-priority" / "policer"'
        ),
    },
)
