"""Lark Transformer that replicates Trigger's SimpleParse IOS ACL dispatch handlers."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lark import Transformer, Token, Tree, v_args, Discard

from trigger.acl.support import (
    ACL, Term, Matches, Modifiers, Comment, TIP, Protocol, RangeList,
    do_protocol_lookup, do_port_lookup, do_icmp_type_lookup, do_icmp_code_lookup,
    make_inverse_mask, Comments, strip_comments,
)
from trigger.acl.dicts import (
    ports, icmp_types, icmp_codes, ios_icmp_messages,
    tcp_flag_specials,
)
from trigger.acl.ios import (
    Remark, inverse_mask_table, handle_ios_match, handle_ios_acl,
    unary_port_operators,
)
from trigger import exceptions

# Sentinel for "any" keyword (distinct from None which Lark uses for missing optionals)
_ANY = object()


class IOSACLTransformer(Transformer):
    """Transform a Lark parse tree into Trigger ACL objects."""

    def start(self, items):
        # Filter out None items (from empty lines, newlines)
        flat = []
        for item in items:
            if item is None:
                continue
            if isinstance(item, Comment):
                continue  # Already pushed to Comments in icomment()
            elif isinstance(item, list):
                flat.extend(item)
            elif isinstance(item, dict):
                flat.append(item)
        return handle_ios_acl(flat)

    # --- ACL structure ---

    def ios_acl_line(self, items):
        return items[0]

    def ios_acl_match_line(self, items):
        digits = str(items[0])
        action_match = items[1]
        action_match["name"] = digits
        action_match["format"] = "ios"
        return action_match

    def ios_acl_no_line(self, items):
        return {"no": True, "name": str(items[0])}

    def ios_ext_line(self, items):
        return items[0]

    def ios_ext_name_line(self, items):
        return {"name": str(items[0]), "format": "ios_named"}

    def ios_ext_no_line(self, items):
        return {"no": True, "name": str(items[0])}

    def ios_rebind_acl_line(self, items):
        return {"name": str(items[0]), "format": "ios_brocade"}

    def ios_rebind_receive_acl_line(self, items):
        return {"name": str(items[0]), "format": "ios_brocade", "receive_acl": True}

    def ios_action_match(self, items):
        action = str(items[0])
        match_dict = items[1]
        return {"term": Term(action=action, **match_dict)}

    # --- Match handlers ---
    # These all build args for handle_ios_match: [protocol, source, dest, *extra]

    def ios_match(self, items):
        # [protocol_or_None, ios_ip, ios_ip, optional_log...]
        protocol = items[0]  # None for 'ip', Protocol for others
        source = self._resolve_any(items[1])
        dest = self._resolve_any(items[2])
        extra = [x for x in items[3:] if x is not None]
        return handle_ios_match([protocol, source, dest] + extra)

    def ios_tcp_port_match(self, items):
        # [TCP_token, ios_ip_port, ios_ip_port, established?, log?]
        protocol = Protocol("tcp")
        source = self._resolve_ip_port(items[1])
        dest = self._resolve_ip_port(items[2])
        extra = [x for x in items[3:] if x is not None]
        return handle_ios_match([protocol, source, dest] + extra)

    def ios_udp_port_match(self, items):
        protocol = Protocol("udp")
        source = self._resolve_ip_port(items[1])
        dest = self._resolve_ip_port(items[2])
        extra = [x for x in items[3:] if x is not None]
        return handle_ios_match([protocol, source, dest] + extra)

    def ios_icmp_match(self, items):
        # [ICMP_token, ios_ip, ios_ip, log?, icmp_message_or_type?, icmp_code?, log?]
        protocol = Protocol("icmp")
        source = self._resolve_any(items[1])
        dest = self._resolve_any(items[2])
        extra = [x for x in items[3:] if x is not None]
        return handle_ios_match([protocol, source, dest] + extra)

    def _resolve_any(self, val):
        """Convert _ANY sentinel to None (what handle_ios_match expects for 'any')."""
        if val is _ANY:
            return None
        return val

    def _resolve_ip_port(self, val):
        """For ios_ip_port results: either a TIP/_ANY or [TIP, RangeList]."""
        if isinstance(val, list):
            # [ip_or_any, port_rangelist]
            return [self._resolve_any(val[0]), val[1]]
        return self._resolve_any(val)

    # --- IP addresses ---

    def ios_ip(self, items):
        return items[0]

    def KW_ANY(self, token):
        return _ANY

    def host_ipv4(self, items):
        return items[0]

    def ios_masked_ipv4(self, items):
        ip = items[0]
        mask_str = str(items[1])
        mask_tip = TIP(mask_str)
        prefix_len = inverse_mask_table[mask_tip]
        return TIP(f"{ip}/{prefix_len}")

    def ipv4(self, items):
        return TIP(str(items[0]))

    def ios_ip_port(self, items):
        # items[0] = ios_ip result (TIP, _ANY)
        # items[1] = optional port result (from unary_port or ios_range)
        ip = items[0]
        if len(items) > 1 and items[1] is not None:
            return [ip, RangeList(items[1])]
        return ip

    # --- Port operators ---

    def unary_port(self, items):
        op = str(items[0])
        port_val = items[1]
        return unary_port_operators[op](port_val)

    def ios_range(self, items):
        return [(items[0], items[1])]

    # --- Protocols ---

    def protocol(self, items):
        return do_protocol_lookup(str(items[0]))

    def KW_IP(self, token):
        return None

    def TCP(self, token):
        return Protocol("tcp")

    def UDP(self, token):
        return Protocol("udp")

    def ICMP(self, token):
        return Protocol("icmp")

    def ESTABLISHED(self, token):
        return "established"

    # --- Ports ---

    def port(self, items):
        return do_port_lookup(str(items[0]))

    # --- ICMP ---

    def icmp_type(self, items):
        return do_icmp_type_lookup(str(items[0]))

    def icmp_code(self, items):
        return do_icmp_code_lookup(str(items[0]))

    def ios_icmp_message(self, items):
        name = str(items[0])
        return ios_icmp_messages[name]

    # --- Logging ---

    def ios_log(self, items):
        # NOTE: handle_ios_match checks `if "log" in extra` and sets syslog=True.
        # The original SimpleParse parser also discards the log/log-input distinction.
        # TODO: Preserve "log-input" vs "log" when handle_ios_match is updated to
        # support it (pre-existing limitation, not introduced by Lark port).
        return "log"

    # --- Comments and remarks ---

    def icomment(self, items):
        body = ""
        for item in items:
            if isinstance(item, Token) and item.type == "ICOMMENT_BODY":
                body = str(item)
        comment = Comment(body)
        Comments.append(comment)
        return None

    def ios_remark_line(self, items):
        # In SimpleParse, remark returns the Remark object which becomes a Comment
        # on the next Term. We replicate by pushing to global Comments.
        remark_body = ""
        for item in items:
            if isinstance(item, Token) and item.type == "REMARK_BODY":
                remark_body = str(item)
        Comments.append(Remark(remark_body))
        return None  # Don't generate a term

    def NEWLINE(self, token):
        return None

    def __default_token__(self, token):
        return token
