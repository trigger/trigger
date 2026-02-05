#!/usr/bin/env python

"""Interface with the access-control list (ACL) database and task queue.

This is a simple command to manage explicit ACL associations within the ACL
database (acls.db), to search for both implicit and explicit ACL associations,
and to manage the ACL task queue.
"""

__version__ = "1.6.1"

import optparse
import sys
from collections import defaultdict
from textwrap import wrap

from trigger import exceptions
from trigger.acl.db import AclsDB, get_matching_acls
from trigger.acl.queue import Queue
from trigger.conf import settings
from trigger.utils.cli import get_terminal_width


def parse_args(argv, optp):
    usage = """
        %prog --display [--exact | --device-name-only] (<acl_name> | <device>)
        %prog (--add | --remove) <acl_name> [<device> [<device> ...]]
        %prog (--clear | --inject) [--quiet] [<acl_name> [<acl_name> ...]]
        %prog (--list | --listmanual)"""

    # Parse arguments.
    optp.usage = usage
    optp.description = __doc__.strip()
    optp.version = __version__
    optp.add_option(
        "-l",
        "--list",
        help="list ACLs currently in integrated (automated) queue",
        action="store_const",
        const="list",
        dest="mode",
    )
    optp.add_option(
        "-m",
        "--listmanual",
        help="list entries currently in manual queue",
        action="store_const",
        const="listmanual",
        dest="mode",
    )
    optp.add_option(
        "-i",
        "--inject",
        help="inject into load queue",
        action="store_const",
        const="inject",
        dest="mode",
    )
    optp.add_option(
        "-c",
        "--clear",
        help="clear from load queue",
        action="store_const",
        const="clear",
        dest="mode",
    )
    optp.add_option(
        "-D",
        "--display",
        help="display the ACL associations for a device or ACL",
        action="store_true",
    )
    optp.add_option(
        "-x",
        "--exact",
        help="match entire name, not just start",
        action="store_true",
        dest="exact",
    )
    optp.add_option(
        "-d",
        "--device-name-only",
        help="don't match on ACL",
        action="store_true",
        dest="dev_only",
    )
    optp.add_option(
        "-a",
        "--add",
        type="string",
        action="append",
        metavar="<acl_name>",
        help="add an acl to explicit ACL database, example: 'acl -a acl-name device1 device2'",
    )
    optp.add_option(
        "-r",
        "--remove",
        type="string",
        action="append",
        metavar="<acl_name>",
        help="remove an acl from explicit ACL database, example: 'acl -r acl1-name -r acl2-name device'",
    )
    optp.add_option(
        "-q",
        "--quiet",
        help="be quiet! (For use with scripts/cron)",
        action="store_true",
    )
    (opts, args) = optp.parse_args()

    return opts, args


def pretty_print_acls(name, acls, term_width, offset=41):
    output = wrap(" ".join(acls), term_width - offset)
    print("%-39s %s" % (name, output[0]))
    for line in output[1:]:
        print(" " * 39, line)


def p_error(optp, msg=None):
    optp.print_help()
    if msg:
        optp.error(msg)
    sys.exit(1)


def main():
    """Main entry point for the CLI tool."""
    # Setup
    aclsdb = AclsDB()
    term_width = get_terminal_width()  # How wide is your term!
    valid_modes = ["list", "listmanual"]  # Valid listing modes

    optp = optparse.OptionParser()
    opts, args = parse_args(sys.argv, optp)

    if opts.add and opts.remove:
        p_error(optp, "cannot both add & remove: pick one.")

    if opts.add or opts.remove:
        if len(args) == 0:
            p_error(optp, "must specify at least one device to modify")

    elif (len(args) == 0 and opts.mode not in valid_modes) or (
        len(args) != 0 and opts.mode in valid_modes
    ):
        p_error(optp)
        sys.exit(1)

    queue = Queue()

    if opts.mode == "list":
        acl_data = defaultdict(list)
        [acl_data[acl].append(router) for router, acl in queue.list()]
        if acl_data:
            [
                pretty_print_acls(dev, acl_data[dev], term_width)
                for dev in sorted(acl_data)
            ]
        else:
            print("Nothing in the integrated queue.")

    elif opts.mode == "listmanual":
        for item, user, ts, _done in queue.list(queue="manual"):
            print(item)
            print(f"\tadded by {user} on {ts}")
            print()
        if not queue.list(queue="manual"):
            print("Nothing in the manual queue.")

    elif opts.mode == "inject":
        for arg in args:
            devs = [dev[0] for dev in get_matching_acls([arg])]
            queue.insert(arg, devs)

    elif opts.mode == "clear":
        [queue.delete(arg) for arg in args]

    elif opts.add or opts.remove:
        from trigger.netdevices import NetDevices

        nd = NetDevices()

        invalid_dev_count = 0

        for arg in args:
            try:
                dev = nd.find(arg.lower())
            except KeyError:
                print(f"skipping {arg}: invalid device")
                invalid_dev_count += 1
                continue
                # the continue here leads that single error if its the only attempt

            if opts.add:
                for acl in opts.add:
                    try:
                        print(aclsdb.add_acl(dev, acl))
                    except exceptions.ACLSetError as err:  # noqa: PERF203
                        print(err)

            elif opts.remove:
                for acl in opts.remove:
                    try:
                        print(aclsdb.remove_acl(dev, acl))
                    except exceptions.ACLSetError as err:  # noqa: PERF203
                        # Check if it is an implicit ACL
                        if acl in aclsdb.get_acl_set(dev, "implicit"):
                            print(f"This ACL is associated via {settings.AUTOACL_FILE}")
                        else:
                            print(err)

        if invalid_dev_count == len(args):
            print("\nPlease use --help to find the right syntax.")

    elif opts.display:
        # Pretty-print the device/acls justified to the terminal
        acl_data = get_matching_acls(
            args, opts.exact, match_acl=(not opts.dev_only), match_device=True,
        )
        if not acl_data:
            msg = f"No results for {args}" if not opts.quiet else 1
            sys.exit(msg)

        [pretty_print_acls(name, acls, term_width) for name, acls in acl_data]
    else:  # No options were handled, display help and exit
        p_error(optp)


if __name__ == "__main__":
    main()
