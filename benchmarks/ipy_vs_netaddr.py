#!/usr/bin/env python
"""
Benchmark: IPy vs netaddr for Trigger ACL workloads.

Tests the operations that matter for Trigger's ACL parser:
1. Object creation (single IPs, networks, /32s)
2. Containment checks (ip in network)
3. Network iteration (host enumeration)
4. Prefix length / version introspection
5. String parsing (various formats)
6. Comparison / sorting (ACL ordering)
7. Bulk operations (simulating large ACL processing)

Usage: python benchmarks/ipy_vs_netaddr.py
"""

import random
import statistics
import time
from contextlib import contextmanager

import IPy
import netaddr


# ---------------------------------------------------------------------------
# Test data — realistic ACL-scale workloads
# ---------------------------------------------------------------------------

# Common ACL entries (mix of hosts, /24s, /16s, /8s)
SINGLE_IPS = [f"10.{a}.{b}.{c}" for a in range(10) for b in range(10) for c in range(10)]  # 1000
NETWORKS_CIDR = [f"192.168.{i}.0/24" for i in range(256)]
NETWORKS_MIXED = [
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
    "10.10.0.0/16", "10.20.0.0/16", "10.30.0.0/16",
    "172.16.10.0/24", "172.16.20.0/24", "172.16.30.0/24",
    "192.168.1.0/24", "192.168.2.0/24", "192.168.3.0/24",
]
LARGE_ACL = [f"10.{a}.{b}.0/24" for a in range(50) for b in range(50)]  # 2500 entries


@contextmanager
def timer(label, results_dict, key):
    """Context manager to time a block and store result."""
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    results_dict[key] = elapsed


def bench_creation_single(n=5):
    """Create IP objects from single addresses."""
    results = {"ipy": [], "netaddr": []}
    for _ in range(n):
        t0 = time.perf_counter()
        objs = [IPy.IP(ip) for ip in SINGLE_IPS]
        results["ipy"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        objs = [netaddr.IPAddress(ip) for ip in SINGLE_IPS]
        results["netaddr"].append(time.perf_counter() - t0)

    return "Creation (1000 single IPs)", results


def bench_creation_networks(n=5):
    """Create network objects from CIDR notation."""
    results = {"ipy": [], "netaddr": []}
    for _ in range(n):
        t0 = time.perf_counter()
        objs = [IPy.IP(net, make_net=True) for net in NETWORKS_CIDR]
        results["ipy"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        objs = [netaddr.IPNetwork(net) for net in NETWORKS_CIDR]
        results["netaddr"].append(time.perf_counter() - t0)

    return "Creation (256 networks)", results


def bench_containment(n=5):
    """Check if IPs are contained in networks."""
    ipy_nets = [IPy.IP(net, make_net=True) for net in NETWORKS_MIXED]
    na_nets = [netaddr.IPNetwork(net) for net in NETWORKS_MIXED]
    test_ips = random.sample(SINGLE_IPS, 200)

    results = {"ipy": [], "netaddr": []}
    for _ in range(n):
        t0 = time.perf_counter()
        for ip in test_ips:
            ipy_ip = IPy.IP(ip)
            for net in ipy_nets:
                _ = ipy_ip in net
        results["ipy"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        for ip in test_ips:
            na_ip = netaddr.IPAddress(ip)
            for net in na_nets:
                _ = na_ip in net
        results["netaddr"].append(time.perf_counter() - t0)

    return "Containment (200 IPs × 12 nets)", results


def bench_containment_ipset(n=5):
    """Containment using netaddr.IPSet (optimized) vs IPy linear scan."""
    ipy_nets = [IPy.IP(net, make_net=True) for net in NETWORKS_MIXED]
    na_ipset = netaddr.IPSet(NETWORKS_MIXED)
    test_ips = random.sample(SINGLE_IPS, 200)

    results = {"ipy": [], "netaddr_ipset": []}
    for _ in range(n):
        t0 = time.perf_counter()
        for ip in test_ips:
            ipy_ip = IPy.IP(ip)
            for net in ipy_nets:
                _ = ipy_ip in net
        results["ipy"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        for ip in test_ips:
            _ = netaddr.IPAddress(ip) in na_ipset
        results["netaddr_ipset"].append(time.perf_counter() - t0)

    return "Containment w/ IPSet (200 IPs)", results


def bench_prefix_introspection(n=5):
    """Access prefix length, version, network attributes."""
    ipy_nets = [IPy.IP(net, make_net=True) for net in NETWORKS_CIDR]
    na_nets = [netaddr.IPNetwork(net) for net in NETWORKS_CIDR]

    results = {"ipy": [], "netaddr": []}
    for _ in range(n):
        t0 = time.perf_counter()
        for net in ipy_nets:
            _ = net.prefixlen()
            _ = net.version()
            _ = net.net()
            _ = net.broadcast()
        results["ipy"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        for net in na_nets:
            _ = net.prefixlen
            _ = net.version
            _ = net.network
            _ = net.broadcast
        results["netaddr"].append(time.perf_counter() - t0)

    return "Prefix introspection (256 nets)", results


def bench_sorting(n=5):
    """Sort a large list of network objects (ACL ordering)."""
    shuffled_cidrs = LARGE_ACL.copy()
    random.shuffle(shuffled_cidrs)

    results = {"ipy": [], "netaddr": []}
    for _ in range(n):
        ipy_objs = [IPy.IP(net, make_net=True) for net in shuffled_cidrs]
        t0 = time.perf_counter()
        ipy_objs.sort()
        results["ipy"].append(time.perf_counter() - t0)

        na_objs = [netaddr.IPNetwork(net) for net in shuffled_cidrs]
        t0 = time.perf_counter()
        na_objs.sort()
        results["netaddr"].append(time.perf_counter() - t0)

    return "Sorting (2500 networks)", results


def bench_str_roundtrip(n=5):
    """Create objects and convert back to strings."""
    results = {"ipy": [], "netaddr": []}
    for _ in range(n):
        t0 = time.perf_counter()
        for net in LARGE_ACL:
            _ = str(IPy.IP(net, make_net=True))
        results["ipy"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        for net in LARGE_ACL:
            _ = str(netaddr.IPNetwork(net))
        results["netaddr"].append(time.perf_counter() - t0)

    return "String roundtrip (2500 nets)", results


def bench_iteration(n=3):
    """Iterate hosts in /24 networks."""
    test_nets = NETWORKS_CIDR[:20]  # 20 /24s = 5120 hosts
    results = {"ipy": [], "netaddr": []}
    for _ in range(n):
        t0 = time.perf_counter()
        for net in test_nets:
            for _ in IPy.IP(net, make_net=True):
                pass
        results["ipy"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        for net in test_nets:
            for _ in netaddr.IPNetwork(net):
                pass
        results["netaddr"].append(time.perf_counter() - t0)

    return "Host iteration (20 × /24)", results


def bench_supernet_merge(n=5):
    """Merge/summarize adjacent networks (netaddr cidr_merge vs manual)."""
    # netaddr has cidr_merge; IPy has no built-in equivalent
    adjacent = [f"10.0.{i}.0/24" for i in range(64)]

    results = {"netaddr_merge": []}
    for _ in range(n):
        t0 = time.perf_counter()
        _ = netaddr.cidr_merge([netaddr.IPNetwork(n) for n in adjacent])
        results["netaddr_merge"].append(time.perf_counter() - t0)

    return "CIDR merge (64 adjacent /24s)", results


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def format_results(label, results):
    """Pretty-print benchmark results."""
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")

    keys = list(results.keys())
    medians = {}
    for key in keys:
        vals = results[key]
        med = statistics.median(vals)
        medians[key] = med
        print(f"  {key:>20s}: {med*1000:8.2f} ms  (n={len(vals)}, stdev={statistics.stdev(vals)*1000:.2f} ms)" if len(vals) > 1 else f"  {key:>20s}: {med*1000:8.2f} ms")

    # Show ratio if exactly 2 comparable keys
    comparable = [k for k in keys if k in ("ipy", "netaddr")]
    if len(comparable) == 2:
        ratio = medians["netaddr"] / medians["ipy"] if medians["ipy"] > 0 else float("inf")
        if ratio > 1:
            print(f"  {'→ IPy is':>20s}: {ratio:.2f}× faster")
        else:
            print(f"  {'→ netaddr is':>20s}: {1/ratio:.2f}× faster")


def main():
    print("=" * 60)
    print("  IPy vs netaddr Benchmark for Trigger ACL Workloads")
    print(f"  IPy version: {IPy.__version__}")
    print(f"  netaddr version: {netaddr.__version__}")
    print("=" * 60)

    benchmarks = [
        bench_creation_single,
        bench_creation_networks,
        bench_containment,
        bench_containment_ipset,
        bench_prefix_introspection,
        bench_sorting,
        bench_str_roundtrip,
        bench_iteration,
        bench_supernet_merge,
    ]

    all_results = []
    for bench in benchmarks:
        label, results = bench()
        format_results(label, results)
        all_results.append((label, results))

    # Summary
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    for label, results in all_results:
        comparable = {k: statistics.median(v) for k, v in results.items() if k in ("ipy", "netaddr")}
        if len(comparable) == 2:
            ratio = comparable["netaddr"] / comparable["ipy"] if comparable["ipy"] > 0 else 0
            winner = "IPy" if ratio > 1 else "netaddr"
            factor = ratio if ratio > 1 else 1/ratio
            print(f"  {label:<40s} → {winner} {factor:.2f}×")
        else:
            for k, v in results.items():
                med = statistics.median(v)
                print(f"  {label:<40s} → {k}: {med*1000:.2f} ms")


if __name__ == "__main__":
    main()
