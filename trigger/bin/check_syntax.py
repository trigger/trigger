#!/usr/bin/env python3

"""check_syntax - Determines if ACL passes parsing check."""

__version__ = "1.0"

import optparse
import os
import sys
import tempfile
from pathlib import Path

from twisted.python import log

from trigger.acl.parser import parse as acl_parse

CONTEXT = 3


def parse_args(argv):
    optp = optparse.OptionParser(
        description="""\
        Determine if ACL file passes trigger's parsing checks.""",
        usage="%prog [opts] file",
    )
    optp.add_option("-q", "--quiet", action="store_true", help="suppress output")
    (opts, args) = optp.parse_args(argv)

    return opts, args


def main():
    """Main entry point for the CLI tool."""
    global opts

    fd, _tmpfile = tempfile.mkstemp(suffix="_parsing_check")
    log.startLogging(os.fdopen(fd, "a"), setStdout=False)
    log.msg(
        'User %s (uid:%d) executed "%s"'
        % (os.environ["LOGNAME"], os.getuid(), " ".join(sys.argv)),
    )

    opts, args = parse_args(sys.argv)

    for file in args[1:]:
        if not Path(file).exists():
            print(f"Moving on.  File does not exist: {file}")
            continue
        if not Path(file).is_file():
            print(f"Moving on.  Not a normal file: {file}")
            continue
        # Calling `read()` on the fd immediately closes it
        with Path(file).open() as fh:
            file_contents = fh.read()

        try:
            acl_parse(file_contents)
            print(f"File {file} passes the syntax check.")
        except Exception as e:
            print(f"File {file} FAILED the syntax check.  Here is the error:")
            print(e)
            print()


if __name__ == "__main__":
    main()
