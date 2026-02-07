#!/usr/bin/env python3

"""gong (go ng) - Command-line client to log in to network devices using TACACS credentials.

An optional .gorc file may be used to specify user preferences.

Partially adapted from conch.  See twisted.conch.scripts.conch and
http://twistedmatrix.com/projects/conch/documentation/howto/conch_client.html
"""

__version__ = "2.0"

import os
import sys
from optparse import OptionParser

from twisted.python import log

# Put this here until the default changes to not load ACLs from redis.
from trigger.conf import settings
from trigger.netdevices import device_match

settings.WITH_ACLS = False


def parse_args(argv):  # noqa: D103
    parser = OptionParser(
        usage="%prog [options] [device]",
        description="""\
Automatically log into network devices using cached TACACS credentials.
""",
    )

    parser.add_option(
        "-o",
        "--oob",
        action="store_true",
        help="Connect to device out of band first.",
    )

    opts, args = parser.parse_args(argv)

    if len(args) != 2:  # noqa: PLR2004
        parser.print_help()
        sys.exit(2)

    return opts, args


def connect_to_oob(dev):
    """Lookup out-of-band info and try to connect to the console using telnet."""
    tn = f"telnet {dev.OOBTerminalServerFQDN} {dev.OOBTerminalServerTCPPort}"

    print(f"OOB Information for {dev.nodeName}:")
    print(tn)
    print("Connecting you now...")
    os.system(tn)


def main():
    """Main entry point for the CLI tool."""
    global opts
    opts, args = parse_args(sys.argv)

    if os.getenv("DEBUG") is not None:
        log.startLogging(sys.stdout, setStdout=False)

    # Exception handling is done in device_match, returns None if no match.
    dev = device_match(args[1].lower(), production_only=False)
    if dev is None:
        return 2

    if dev.adminStatus != "PRODUCTION":
        print("WARNING: You are connecting to a non-production device.")

    if opts.oob:
        connect_to_oob(dev)
        return 0

    # Connect to the device... and make sure to capture its exit code
    retval = dev.connect()

    print("\n")  # Return cursor to beginning of line
    return retval


if __name__ == "__main__":
    sys.exit(main())
