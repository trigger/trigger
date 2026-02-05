#!/usr/bin/env python

"""fe - the File Editor. Uses RCS to maintain ACL policy versioning.
"""

__version__ = "1.2.1"


import os
import re
import sys
from pathlib import Path

from simpleparse.error import ParserSyntaxError

from trigger import acl
from trigger.acl.parser import TIP
from trigger.utils.cli import yesno

psa_checks = (
    (lambda t: "source-port" in t.match, "source port"),
    (lambda t: "tos" in t.match, "ToS"),
    (lambda t: "precedence" in t.match, "precedence"),
    (lambda t: "protocol" in t.match and "igmp" in t.match["protocol"], "IGMP"),
)


def gsr_checks(a):
    """PSA and SALSA checks, if the ACL is tagged appropriately."""
    ok = True
    max_lines, psa = None, False
    if [c for c in a.comments if "SALSA" in c]:
        max_lines = 128
    elif [c for c in a.comments if "PSA-128" in c]:
        max_lines, psa = 128, True
    elif [c for c in a.comments if "PSA-448" in c]:
        max_lines, psa = 448, True
    if max_lines and len(a.terms) > max_lines:
        print("ACL has %d lines, max %d (GSR limit)" % (len(a.terms), max_lines))
        ok = False
    if psa:
        for t in a.terms:
            for check, reason in psa_checks:
                if check(t):
                    print(f"Match on {reason} not permitted in PSA mode")
                    for line in t.output_ios():
                        print("    " + line)
                    ok = False
    return ok


def normalize(a):
    """Fix up the ACL, and return False if there are problems."""
    if isinstance(a, acl.PolicerGroup):
        return True

    ok = True

    # JunOS counter policy and duplicate term names.
    if a.format == "junos":
        names = set()
        for t in a.terms:
            if t.name in names:
                print("Duplicate term name", t.name)
                ok = False
            else:
                names.add(t.name)

    # GSR checks.
    if a.format == "ios" and not gsr_checks(a):  # not ios_named
        ok = False

    # Check for 10/8.
    for t in a.terms:
        for addr in ("address", "source-address", "destination-address"):
            for block in t.match.get(addr, []):
                if block == TIP("10.0.0.0/8"):
                    print("Matching on 10.0.0.0/8 is never correct")
                    for line in t.output(a.format):
                        print("    " + line)
                    ok = False

    # Here is the place to put other policy checks; for example, we could
    # check blue to green HTTP and make sure all those terms have a comment
    # in a standardized format saying it was approved.

    return ok


def edit(editfile):
    """Edits the file and calls normalize(). Loops until it passes or the user
    confirms they want to bypass failed normalization. Returns a file object of
    the diff output.
    """
    editor = os.environ.get("EDITOR", "vim")
    if editor.startswith("vi"):
        os.spawnlp(
            os.P_WAIT, editor, editor, "+set sw=4", "+set softtabstop=4", editfile,
        )
    else:
        os.spawnlp(os.P_WAIT, editor, editor, editfile)

    if Path(editfile).name:  # .startswith('acl.'):
        print("Normalizing ACL...")
        a = None
        try:
            with Path(editfile).open() as fh:
                a = acl.parse(fh)
        except ParserSyntaxError as e:
            print(e)
        except TypeError as e:
            print(e)
        except Exception as e:
            print("ACL parse failed: ", sys.exc_info()[0], ":", e)
        if a and normalize(a):
            output = "\n".join(a.output(replace=True)) + "\n"
            with Path(editfile).open("w") as fh:
                fh.write(output)
        elif yesno("Re-edit?"):
            return edit(editfile)

    # should use a list version of popen
    return os.popen("rcsdiff -u -b -q " + editfile).read()


def main():
    """Main entry point for the CLI tool."""
    if len(sys.argv) < 2:
        print("usage: fe files...", file=sys.stderr)
        sys.exit(2)

    for editfile in sys.argv[1:]:
        try:
            stat = Path(editfile).stat()
        except OSError:
            stat = None

        if not stat:
            if yesno(f"{editfile} does not exist; create?", False):
                edit(editfile)
                os.spawnlp(os.P_WAIT, "ci", "ci", "-u", editfile)

        else:
            rv = os.spawnlp(os.P_WAIT, "co", "co", "-f", "-l", editfile)
            if rv:
                print("couldn't check out " + editfile, file=sys.stderr)
                continue

            diff = edit(editfile)
            if not diff:
                print("No changes made.")
                os.spawnlp(os.P_WAIT, "rcs", "rcs", "-u", editfile)
                # When no changes are made, ci leaves the file writable.
                Path(editfile).chmod(stat.st_mode & 0o555)
                continue

            print()
            print(f'"{Path(editfile).name}"')
            print("BEGINNING OF CHANGES========================")
            print(diff, end="")
            print("END OF CHANGES==============================")
            print()
            print()

            if not yesno("Do you want to save changes?"):
                print("Restoring original file")
                os.spawnlp(os.P_WAIT, "co", "co", "-f", "-u", editfile)
                continue

            # Try to auto-detect log message from comments.
            log = ""
            pats = (re.compile(r"^\+.*!+(.*)"), re.compile(r"^\+.*/\*(.*)\*/"))
            for line in diff.split("\n"):
                for pat in pats:
                    m = pat.match(line)
                    if m:
                        msg = m.group(1).strip()
                        if msg:
                            log += m.group(1).strip() + "\n"
                        break
            if log:
                print("Autodetected log message:")
                print(log)
                print()
                if not yesno("Use this?"):
                    log = ""

            if log:
                os.spawnlp(os.P_WAIT, "ci", "ci", "-u", "-m" + log, editfile)
            else:
                os.spawnlp(os.P_WAIT, "ci", "ci", "-u", editfile)


if __name__ == "__main__":
    main()
