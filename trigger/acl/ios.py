from support import Comment, Remark
from trigger import exceptions
from trigger.conf import settings
from grammar import *

#
# IOS-like ACLs.
#

def make_inverse_mask(prefixlen):
    """
    Return an IP object of the inverse mask of the CIDR prefix.

    :param prefixlen:
        CIDR prefix
    """
    inverse_bits = 2 ** (32 - prefixlen) - 1
    return TIP(inverse_bits)

# Build a table to unwind Cisco's weird inverse netmask.
# TODO (jathan): These don't actually get sorted properly, but it doesn't seem
# to have mattered up until now. Worth looking into it at some point, though.
inverse_mask_table = dict([(make_inverse_mask(x), x) for x in range(0, 33)])

def handle_ios_match(a):
    protocol, source, dest = a[:3]
    extra = a[3:]

    match = Matches()
    modifiers = Modifiers()

    if protocol:
        match['protocol'] = [protocol]

    for sd, arg in (('source', source), ('destination', dest)):
        if isinstance(arg, list):
            if arg[0] is not None:
                match[sd + '-address'] = [arg[0]]
            match[sd + '-port'] = arg[1]
        else:
            if arg is not None:
                match[sd + '-address'] = [arg]

    if 'log' in extra:
        modifiers['syslog'] = True
        extra.remove('log')

    if protocol == 'icmp':
        if len(extra) > 2:
            raise NotImplementedError(extra)
        if extra and isinstance(extra[0], tuple):
            extra = extra[0]
        if len(extra) >= 1:
            match['icmp-type'] = [extra[0]]
        if len(extra) >= 2:
            match['icmp-code'] = [extra[1]]
    elif protocol == 'tcp':
        if extra == ['established']:
            match['tcp-flags'] = [tcp_flag_specials['tcp-established']]
        elif extra:
            raise NotImplementedError(extra)
    elif extra:
        raise NotImplementedError(extra)

    return {'match': match, 'modifiers': modifiers}

def handle_ios_acl(rows):
    acl = ACL()
    for d in rows:
        if not d:
            continue
        for k, v in d.iteritems():
            if k == 'no':
                acl = ACL()
            elif k == 'name':
                if acl.name:
                    if v != acl.name:
                        raise exceptions.ACLNameError("Name '%s' does not match ACL '%s'" % (v, acl.name))
                else:
                    acl.name = v
            elif k == 'term':
                acl.terms.append(v)
            elif k == 'format':
                acl.format = v
            # Brocade receive-acl
            elif k == 'receive_acl':
                acl.is_receive_acl = True
            else:
                raise RuntimeError('unknown key "%s" (value %s)' % (k, v))
    # In traditional ACLs, comments that belong to the first ACE are
    # indistinguishable from comments that belong to the ACL.
    #if acl.format == 'ios' and acl.terms:
    if acl.format in ('ios', 'ios_brocade') and acl.terms:
        acl.comments += acl.terms[0].comments
        acl.terms[0].comments = []
    return acl

unary_port_operators = {
    'eq':   lambda x: [x],
    'le':   lambda x: [(0, x)],
    'lt':   lambda x: [(0, x-1)],
    'ge':   lambda x: [(x, 65535)],
    'gt':   lambda x: [(x+1, 65535)],
    'neq':  lambda x: [(0, x-1), (x+1, 65535)]
}

rules.update({
    'ios_ip':                    'kw_any / host_ipv4 / ios_masked_ipv4',
    'kw_any':                    ('"any"', None),
    'host_ipv4':            '"host", ts, ipv4',
    S('ios_masked_ipv4'):   ('ipv4, ts, ipv4_inverse_mask',
                             lambda (net, length): TIP('%s/%d' % (net, length))),
    'ipv4_inverse_mask':    (literals(inverse_mask_table),
                             lambda x: inverse_mask_table[TIP(x)]),

    'kw_ip':                    ('"ip"', None),
    S('ios_match'):            ('kw_ip / protocol, ts, ios_ip, ts, ios_ip, '
                             '(ts, ios_log)?',
                             handle_ios_match),
    S('ios_tcp_port_match'):('tcp, ts, ios_ip_port, ts, ios_ip_port, '
                             '(ts, established)?, (ts, ios_log)?',
                             handle_ios_match),
    S('ios_udp_port_match'):('udp, ts, ios_ip_port, ts, ios_ip_port, '
                             '(ts, ios_log)?',
                             handle_ios_match),
    S('ios_ip_port'):            'ios_ip, (ts, unary_port / ios_range)?',
    S('unary_port'):            ('unary_port_operator, ts, port',
                             lambda (op, arg): unary_port_operators[op](arg)),
    'unary_port_operator':  literals(unary_port_operators),
    S('ios_range'):            ('"range", ts, port, ts, port',
                             lambda (x, y): [(x, y)]),
    'established':            '"established"',
    S('ios_icmp_match'):    ('icmp, ts, ios_ip, ts, ios_ip, (ts, ios_log)?, '
                             '(ts, ios_icmp_message / '
                             ' (icmp_type, (ts, icmp_code)?))?, (ts, ios_log)?',
                             handle_ios_match),
    'ios_icmp_message':     (literals(ios_icmp_messages),
                             lambda x: ios_icmp_messages[x]),

    'ios_action':            '"permit" / "deny"',
    'ios_log':                    '"log-input" / "log"',
    S('ios_action_match'):  ('ios_action, ts, ios_tcp_port_match / '
                             'ios_udp_port_match / ios_icmp_match / ios_match',
                             lambda x: {'term': Term(action=x[0], **x[1])}),

    'ios_acl_line':            'ios_acl_match_line / ios_acl_no_line',
    S('ios_acl_match_line'):('"access-list", ts, digits, ts, ios_action_match',
                             lambda x: update(x[1], name=x[0], format='ios')),
    S('ios_acl_no_line'):   ('"no", ts, "access-list", ts, digits',
                             lambda x: {'no': True, 'name': x[0]}),

    'ios_ext_line':          ('ios_action_match / ios_ext_name_line / '
                             'ios_ext_no_line / ios_remark_line / '
                             'ios_rebind_acl_line / ios_rebind_receive_acl_line'),
    S('ios_ext_name_line'): ('"ip", ts, "access-list", ts, '
                             '"extended", ts, word',
                             lambda x: {'name': x[0], 'format': 'ios_named'}),
    S('ios_ext_no_line'):   ('"no", ts, "ip", ts, "access-list", ts, '
                             '"extended", ts, word',
                             lambda x: {'no': True, 'name': x[0]}),
    # Brocade "ip rebind-acl foo" or "ip rebind-receive-acl foo" syntax
    S('ios_rebind_acl_line'): ('"ip", ts, "rebind-acl", ts, word',
                              lambda x: {'name': x[0], 'format': 'ios_brocade'}),

    # Brocade "ip rebind-acl foo" or "ip rebind-receive-acl foo" syntax
    S('ios_rebind_receive_acl_line'): ('"ip", ts, "rebind-receive-acl", ts, word',
                                lambda x: {'name': x[0], 'format': 'ios_brocade',
                                           'receive_acl': True}),

    S('icomment'):            ('"!", ts?, icomment_body', lambda x: x),
    'icomment_body':            ('-"\n"*', Comment),
    S('ios_remark_line'):   ('("access-list", ts, digits_s, ts)?, "remark", ts, remark_body', lambda x: x),
    'remark_body':            ('-"\n"*', Remark),

    '>ios_line<':            ('ts?, (ios_acl_line / ios_ext_line / "end")?, '
                             'ts?, icomment?'),
    S('ios_acl'):            ('(ios_line, "\n")*, ios_line', handle_ios_acl),
})
