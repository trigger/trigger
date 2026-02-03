#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
find_access - Like check_access but reports on networks inside of networks.
"""

from __future__ import print_function

__version__ = "1.6"

from optparse import OptionParser
from simpleparse.error import ParserSyntaxError
import sys
from trigger.acl.parser import parse, TIP


def parse_args(argv):
    parser = OptionParser(
        usage="%prog [options] [acls]",
        add_help_option=False,
        description="a more detailed varient of check_access.",
    )
    desc = """
This is used more for reporting purposes. Currently check_access will do the
right thing for finding access that is requested, but lacks the ability to
report on networks inside networks.

For example if an administrator ran the command:
check_access /netsec/firewalls/acl.131mj 172.16.0.0/12 any

This would only show terms where the source address was specifically
172.168.0.0/12 but nothing smaller. This is due to the fact that if
an engineer wanted to add new access for this range - this wouldn't
actually be the correct access to add.

This script looks in a slighty more detailed manner. If the input
address is 172.16.1.0/24 and a term contains 172.16.1.5/32 that access
would be reported on.

This works in reverse, if the input is 172.16.1.0/24 and a term contains
172.16.0.0/16 this access is reported.\n"""

    parser.add_option("-h", "--help", action="store_true")
    parser.add_option("-s", "--source-network", help="Supply a source network to find")
    parser.add_option(
        "-d", "--destination-network", help="Supply a destination network to find"
    )
    parser.add_option(
        "-p",
        "--ports",
        help="Specify a set of ports comma seperated, allows for ranges",
    )
    parser.add_option(
        "-S",
        "--no-any-source",
        action="store_true",
        help='Do not include terms with source-address of "any"',
    )
    parser.add_option(
        "-D",
        "--no-any-destination",
        action="store_true",
        help='Do not include terms with destination-address of "any"',
    )

    opts, args = parser.parse_args(argv)

    if opts.help:
        parser.print_help()
        sys.exit(desc)

    return opts, args


def match_term(term, data, type, opts):
    # If any source/dest, return False
    if opts.no_any_source and any_source(term):
        return False
    if opts.no_any_destination and any_dest(term):
        return False

    # If no input data or term field src/dst is any...
    if not data or not term.match.has_key(type):
        return True

    if "port" in type:
        for port in data:
            if port in term.match[type]:
                return True
        return False

    for data_in_term in term.match[type]:
        for data_entry in data:
            if data_entry in data_in_term or data_in_term in data_entry:
                return True

    return False


def match_terms(acl, sources, dests, ports, opts):
    matched = []

    for term in acl.terms:
        matched_sources = False
        matched_dests = False
        matched_ports = False

        matched_sources = match_term(term, sources, "source-address", opts)
        matched_dests = match_term(term, dests, "destination-address", opts)
        matched_ports = match_term(term, ports, "destination-port", opts)

        if matched_sources and matched_dests and matched_ports:
            matched.append(term)

    return matched


def permits_from_any(term):
    """Returns True if action is "accept" and term has no 'source-address'"""
    return term.action[0] == "accept" and not term.match.get("source-address")


def any_source(term):
    """Returns True term has no 'source-address'"""
    return not term.match.get("source-address")


def any_dest(term):
    """Returns True term has no 'destination-address'"""
    return not term.match.get("destination-address")


def do_work(acl_files, opts):
    acl_file_data = {}
    sources = []
    dests = []
    ports = []

    if opts.source_network:
        for x in opts.source_network.split(","):
            sources.append(TIP(x))

    if opts.destination_network:
        for x in opts.destination_network.split(","):
            dests.append(TIP(x))

    if opts.ports:
        for x in opts.ports.split(","):
            ports.append(int(x))

    for acl_file in acl_files:
        try:
            acl = parse(file(acl_file))
        except ParserSyntaxError, e:
            etxt = str(e).split()
            sys.exit(etxt)

        matching_terms = match_terms(acl, sources, dests, ports, opts)

        acl.filename = acl_file  # Store this for a hot minute
        acl.terms = []  # Nuke this in case it's huge
        acl_file_data[acl] = matching_terms

    return acl_file_data


def print_report(data):
    for aclobj, terms in data.items():
        print(aclobj.filename)
        print("=================================================")
        for term in terms:
            for o in term.output(format=aclobj.format, acl_name=aclobj.name):
                print(o)
        print("")


def main():
    """Main entry point for the CLI tool."""
    opts, args = parse_args(sys.argv)

    acls_to_check = args[1:]

    if not opts.source_network and not opts.destination_network or not acls_to_check:
        sys.exit("ERROR: No source or destination networks defined. Try -h for help.")

    data = do_work(acls_to_check, opts)
    print_report(data)


if __name__ == "__main__":
    main()
