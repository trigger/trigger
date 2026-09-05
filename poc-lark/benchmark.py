#!/usr/bin/env python3
"""Benchmark: SimpleParse vs Lark for IOS ACL parsing."""

import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lark import Lark
from ios_transformer import IOSACLTransformer
from trigger.acl.support import Comments
from trigger.acl import parse as simpleparse_parse

GRAMMAR_FILE = os.path.join(os.path.dirname(__file__), "ios_acl.lark")

# Test ACLs of varying complexity
ACLS = {
    "simple": "access-list 123 permit tcp any host 10.20.30.40 eq 80",
    "multi_line": """access-list 100 permit tcp any host 10.0.0.1 eq 80
access-list 100 permit tcp any host 10.0.0.1 eq 443
access-list 100 permit tcp any host 10.0.0.2 eq 22
access-list 100 deny ip any any""",
    "complex": """ip access-list extended COMPLEX-ACL
 permit tcp host 1.2.3.4 host 5.6.7.8 eq 443
 permit tcp 10.0.0.0 0.0.0.255 any range 1024 65535
 permit udp any host 10.0.0.1 eq 53
 permit icmp any any echo
 deny ip any any log""",
}


def make_lark_parser():
    with open(GRAMMAR_FILE) as f:
        grammar = f.read()
    return Lark(grammar, parser="earley")


def lark_parse(parser, text):
    Comments.clear()
    tree = parser.parse(text)
    transformer = IOSACLTransformer()
    return transformer.transform(tree)


def benchmark_one(name, text, iterations):
    print(f"\n--- {name} ({len(text)} chars, {iterations} iterations) ---")

    # SimpleParse
    t0 = time.perf_counter()
    for _ in range(iterations):
        sp_result = simpleparse_parse(text)
    sp_time = time.perf_counter() - t0

    # Lark Earley (fresh parser each time for fairness vs SimpleParse which also creates parser)
    lark_parser = make_lark_parser()
    t0 = time.perf_counter()
    for _ in range(iterations):
        Comments.clear()
        lk_result = lark_parse(lark_parser, text)
    lk_time = time.perf_counter() - t0

    # Lark Earley with reused parser (amortized)
    t0 = time.perf_counter()
    for _ in range(iterations):
        Comments.clear()
        lk_result2 = lark_parse(lark_parser, text)
    lk_reuse_time = time.perf_counter() - t0

    ratio = lk_time / sp_time if sp_time > 0 else float('inf')
    ratio_reuse = lk_reuse_time / sp_time if sp_time > 0 else float('inf')

    print(f"  SimpleParse:        {sp_time:.4f}s ({sp_time/iterations*1000:.2f}ms/parse)")
    print(f"  Lark (Earley):      {lk_time:.4f}s ({lk_time/iterations*1000:.2f}ms/parse) [{ratio:.1f}x]")
    print(f"  Lark (reused):      {lk_reuse_time:.4f}s ({lk_reuse_time/iterations*1000:.2f}ms/parse) [{ratio_reuse:.1f}x]")

    # Correctness check
    sp_terms = [(t.action, str(t.match)) for t in sp_result.terms]
    lk_terms = [(t.action, str(t.match)) for t in lk_result.terms]

    if sp_result.name == lk_result.name and sp_terms == lk_terms:
        print(f"  ✅ Correctness: MATCH (name={sp_result.name}, {len(sp_terms)} terms)")
    else:
        print(f"  ❌ Correctness: MISMATCH")
        if sp_result.name != lk_result.name:
            print(f"    Name: SP={sp_result.name} vs LK={lk_result.name}")
        for i, (sp, lk) in enumerate(zip(sp_terms, lk_terms)):
            if sp != lk:
                print(f"    Term {i}: SP={sp} vs LK={lk}")

    return sp_time, lk_time, lk_reuse_time


def main():
    print("=" * 70)
    print("IOS ACL Parser Benchmark: SimpleParse vs Lark")
    print("=" * 70)

    for iters in [1, 10, 100]:
        print(f"\n{'='*70}")
        print(f"Iterations: {iters}")
        print(f"{'='*70}")
        for name, text in ACLS.items():
            benchmark_one(name, text, iters)

    # LALR test
    print(f"\n{'='*70}")
    print("LALR Compatibility Test")
    print(f"{'='*70}")
    try:
        with open(GRAMMAR_FILE) as f:
            grammar = f.read()
        lalr_parser = Lark(grammar, parser="lalr")
        print("  LALR parser created: YES")
        try:
            Comments.clear()
            tree = lalr_parser.parse(ACLS["simple"])
            transformer = IOSACLTransformer()
            result = transformer.transform(tree)
            print(f"  LALR parse: OK (name={result.name})")
        except Exception as e:
            print(f"  LALR parse: FAILED - {e}")
    except Exception as e:
        print(f"  LALR parser creation: FAILED - {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
