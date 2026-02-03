#!/usr/bin/env python3

"""
aclconv - Converts an ACL, or a list of ACLs, from one format to another.
"""

__version__ = "1.11"

import optparse
import sys

from trigger import acl

formats = {
    "ios": ("i", "IOS old-school"),
    "ios_named": ("o", "IOS named"),
    "junos": ("j", "JunOS"),
    "iosxr": ("x", "IOS XR"),
}


def main():
    """Main entry point for the CLI tool."""
    optp = optparse.OptionParser(
        description="""\
Convert an ACL on stdin, or a list of ACLs, from one format to another.

Input format is determined automatically.  Output format can be given
with -f or with one of -i/-o/-j/-x.

The name of the output ACL is determined automatically, or it can be
specified with -n."""
    )
    optp.add_option("-f", "--format", choices=list(formats.keys()))
    for format, t in formats.items():
        optp.add_option(
            "-" + t[0],
            "--" + format.replace("_", "-"),
            action="store_const",
            const=format,
            dest="format",
            help=f"Use {t[1]} ACL output format",
        )
    optp.add_option("-n", "--name", dest="aclname")
    (opts, files) = optp.parse_args()

    if opts.format is None:
        optp.print_help()
        sys.exit(1)

    if not files or files == ["-"]:
        files = ["/dev/fd/0"]

    for fname in files:
        with open(fname) as f:
            a = acl.parse(f)

        if opts.aclname is not None:
            a.name = opts.aclname
        elif opts.format == "ios" and (a.name is None or not a.name.isdigit()):
            a.name = "100"
        elif opts.format != "ios" and not a.name.endswith(formats[opts.format][0]):
            a.name += formats[opts.format][0]

        if opts.format.startswith("ios"):
            for t in a.terms:
                if t.action == ("discard",):
                    t.action = "reject"
        if opts.format == "junos":
            a.name_terms()
            for t in a.terms:
                if "count" not in t.modifiers:
                    t.modifiers["count"] = t.name
        if opts.format == "iosxr":
            for t in a.terms:
                t.name = None

        print("\n".join(a.output(opts.format, replace=True)))


if __name__ == "__main__":
    main()
