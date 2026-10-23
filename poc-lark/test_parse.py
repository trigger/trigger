#!/usr/bin/env python3
"""Test the Lark IOS ACL parser against various ACL inputs."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lark import Lark
from ios_transformer import IOSACLTransformer
from trigger.acl.support import Comments

GRAMMAR_FILE = os.path.join(os.path.dirname(__file__), "ios_acl.lark")

def make_parser(parser_type="earley"):
    with open(GRAMMAR_FILE) as f:
        grammar = f.read()
    return Lark(grammar, parser=parser_type, propagate_positions=True)

def parse_acl(text, parser_type="earley"):
    """Parse an ACL string and return an ACL object."""
    # Reset global comments
    Comments.clear()
    parser = make_parser(parser_type)
    tree = parser.parse(text)
    transformer = IOSACLTransformer()
    return transformer.transform(tree)


# === Test cases ===

TEST_CASES = {
    "simple_numbered": "access-list 123 permit tcp any host 10.20.30.40 eq 80",

    "simple_deny": "access-list 101 deny udp any any eq 53",

    "named_extended": """ip access-list extended MY-ACL
 permit tcp any host 10.0.0.1 eq 443
 deny ip any any""",

    "icmp_type": "access-list 150 permit icmp any any echo",

    "icmp_type_code": "access-list 150 permit icmp any any unreachable port-unreachable",

    "port_range": "access-list 123 permit tcp any any range 1024 65535",

    "established": "access-list 123 permit tcp any any established",

    "log": "access-list 123 permit tcp any host 10.0.0.1 eq 22 log",

    "log_input": "access-list 123 permit ip any any log-input",

    "neq": "access-list 123 deny tcp any any neq 80",

    "masked_ip": "access-list 123 permit ip 10.0.0.0 0.0.0.255 any",

    "multiple_terms": """access-list 100 permit tcp any host 10.0.0.1 eq 80
access-list 100 permit tcp any host 10.0.0.1 eq 443
access-list 100 deny ip any any""",

    "with_remark": """access-list 100 remark Allow web traffic
access-list 100 permit tcp any host 10.0.0.1 eq 80
access-list 100 deny ip any any""",

    "with_comment": """! This is a comment
access-list 100 permit tcp any host 10.0.0.1 eq 80""",

    "brocade_rebind": """ip rebind-acl MY-BROCADE-ACL
 permit tcp any host 10.0.0.1 eq 80
 deny ip any any""",

    "brocade_receive": """ip rebind-receive-acl MY-RECV-ACL
 permit tcp any host 10.0.0.1 eq 80
 deny ip any any""",

    "icmp_message": "access-list 150 permit icmp any any host-unreachable",

    "host_to_host": "access-list 123 permit tcp host 1.2.3.4 host 5.6.7.8 eq 22",
}


def run_tests():
    passed = 0
    failed = 0
    errors = []

    for name, acl_text in TEST_CASES.items():
        try:
            result = parse_acl(acl_text)
            print(f"  ✅ {name}: name={result.name}, format={result.format}, "
                  f"terms={len(result.terms)}")
            for i, t in enumerate(result.terms):
                print(f"      term[{i}]: action={t.action}, match={t.match}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
            errors.append((name, e))

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed out of {passed+failed}")
    if errors:
        print(f"\nFailed tests:")
        for name, e in errors:
            print(f"  - {name}: {e}")

    return failed == 0


if __name__ == "__main__":
    print("Testing Lark IOS ACL Parser (Earley)")
    print("=" * 60)
    success = run_tests()

    # Try LALR
    print("\n\nTesting LALR mode...")
    print("=" * 60)
    try:
        parser = make_parser("lalr")
        print("  LALR parser created successfully!")
        try:
            result = parse_acl(TEST_CASES["simple_numbered"], "lalr")
            print(f"  LALR parse OK: {result.name}")
        except Exception as e:
            print(f"  LALR parse failed: {e}")
    except Exception as e:
        print(f"  LALR parser creation failed: {type(e).__name__}: {e}")

    sys.exit(0 if success else 1)
