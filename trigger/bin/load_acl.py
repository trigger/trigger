#!/usr/bin/env python

"""load_acl - Unified automatic ACL loader.

By default, ACLs will be loaded on all the devices they apply to (using
acls.db/autoacls).  With ``-f``, that list will be used instead.  With ``-Q``,
the load queue list will be used instead.  For example, ``load_acl -Q 145``
will load on all the devices 145 is queued for.  ``load_acl -Q`` with no
ACLs listed will load everything in the queue. ``load_acl --auto`` will
automatically load eligible devices from the queue and email results.
"""

__version__ = "1.9.2"

# Dist imports
import contextlib
import curses
import datetime
import fnmatch
import logging
import os
import re
import sys
import tempfile
import time
from collections import defaultdict
from optparse import OptionParser
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement

import pytz
from twisted.internet import defer, reactor, task
from twisted.python import log

# Trigger imports
from trigger import exceptions
from trigger.acl.queue import Queue
from trigger.acl.tools import get_bulk_acls, process_bulk_loads
from trigger.conf import settings
from trigger.netdevices import NetDevices
from trigger.tacacsrc import Tacacsrc
from trigger.utils.cli import NullDevice, min_sec, pretty_time, print_severed_head
from trigger.utils.notifications import send_email, send_notification

# Globals
# Pull in these functions from settings
get_current_oncall = settings.GET_CURRENT_ONCALL
create_cm_ticket = settings.CREATE_CM_TICKET
stage_acls = settings.STAGE_ACLS
get_tftp_source = settings.GET_TFTP_SOURCE  # (dev)

# Our global NetDevices object!
nd = NetDevices()  # production_only=False)  #should be added with a flag

# We don't want queue interaction messages to mess up curses display
queue = Queue(verbose=False)

# For displaying acls that were filtered during get_work()
filtered_acls = set()

# Used to keep track of the output of the curses status board.
output_cache = {}


def draw_screen(s, work, active, failures, start_qlen, start_time):
    """Curses-based status board for displaying progress during interactive
    mode.

    :param work:
        The work dictionary (device to acls)

    :param active:
        Dictionary mapping running devs to human-readable status

    :param failures:
        Dictionary of failures

    :param start_qlen:
        The length of the queue at start (to calculate progress)

    :param start_time:
        The epoch time at startup (to calculate progress)
    """
    global output_cache  # noqa: PLW0602

    if not s:
        # this is stuff if we don't have a ncurses handle.
        for device, status in active.items():
            if device in output_cache:
                if output_cache[device] != status:
                    log.msg(f"{device}: {status}")
                    output_cache[device] = status
            else:
                log.msg(f"{device}: {status}")
                output_cache[device] = status
        return

    s.erase()

    # DO NOT cache the result of s.getmaxyx(), or you cause race conditions
    # which can create exceptions when the window is resized.
    def maxx():
        _y, x = s.getmaxyx()
        return x

    def maxy():
        y, _x = s.getmaxyx()
        return y

    # Display progress bar at top (#/devices, elapsed time)
    s.addstr(0, 0, "load_acl"[: maxx()], curses.A_BOLD)
    progress = "  %d/%d devices" % (start_qlen - len(work) - len(active), start_qlen)
    s.addstr(0, maxx() - len(progress), progress)

    doneness = 1 - float(len(work) + len(active)) / start_qlen
    elapsed = time.time() - start_time
    elapsed_str = min_sec(elapsed)

    # Update status
    if doneness == 0:
        remaining_str = " "
    elif doneness == 1:
        remaining_str = "done"
    else:
        remaining_str = min_sec(elapsed / doneness - elapsed)
    max_line = int(maxx() - len(remaining_str) - len(elapsed_str) - 2)

    s.addstr(1, 0, elapsed_str)
    s.addstr(1, maxx() - len(remaining_str), remaining_str)
    s.hline(1, len(elapsed_str) + 1, curses.ACS_HLINE, int(max_line * doneness))

    # If we get failures, report them
    if failures:
        count, plural = len(failures), ((len(failures) > 1 and "s") or "")
        s.addstr(
            2,
            0,
            " %d failure%s, will report at end " % (count, plural),
            curses.A_STANDOUT,
        )

    # Update device name
    for y, (dev, status) in zip(range(3, maxy()), active.items(), strict=False):
        s.addstr(y, 0, (f"{dev}: {status}")[: maxx()], curses.A_BOLD)
    for y, (dev, acls) in zip(range(3 + len(active), maxy()), work.items(), strict=False):
        s.addstr(y, 0, ("{}: {}".format(dev, " ".join(acls)))[: maxx()])

    s.move(maxy() - 1, maxx() - 1)
    s.refresh()


def parse_args(argv):
    """Parses the args and returns opts, args back to caller. Defaults to
    ``sys.argv``, but Optinally takes a custom one if you so desire.

    :param argv:
        A list of opts/args to use over sys.argv
    """

    def comma_cb(option, opt_str, value, parser):
        """OptionParser callback to handle comma-separated arguments."""
        values = value.split(",")
        try:
            getattr(parser.values, option.dest).extend(values)
        except AttributeError:
            setattr(parser.values, option.dest, values)

    parser = OptionParser(usage="%prog [options] [acls]", description=__doc__.lstrip())
    parser.add_option("-f", "--file", help="specify explicit list of devices")
    parser.add_option(
        "-Q",
        "--queue",
        action="store_true",
        help="load ACLs from integrated load queue",
    )
    parser.add_option(
        "-q",
        "--quiet",
        action="store_true",
        help="suppress all standard output; errors/warnings still display",
    )
    parser.add_option(
        "--exclude",
        "--except",
        type="string",
        action="callback",
        callback=comma_cb,
        dest="exclude",
        default=[],
        help="skip over ACLs or devices; shell-type patterns "
        '(e.g., "iwg?-[md]*") can be used for devices; for '
        "multiple excludes, use commas or give this option "
        "more than once",
    )
    parser.add_option(
        "-j",
        "--jobs",
        type="int",
        default=5,
        help="maximum simultaneous connections (default 5)",
    )
    # Booleans below
    parser.add_option(
        "-e",
        "--escalation",
        "--escalated",
        action="store_true",
        help="load escalated ACLs from integrated load queue",
    )
    parser.add_option(
        "--severed-head", action="store_true", help="display severed head",
    )
    parser.add_option(
        "--no-db", action="store_true", help="disable database access (for outages)",
    )
    parser.add_option(
        "--bouncy", action="store_true", help="load out of bounce (override checks)",
    )
    parser.add_option(
        "--no-vip", action="store_true", help="TFTP from green address, not blue VIP",
    )
    parser.add_option(
        "--bulk",
        action="store_true",
        help="force all loads to be treated as bulk, restricting "
        "the amount of devices that will be loaded per "
        "execution of load_acl.",
    )
    parser.add_option(
        "--no-cm", action="store_true", help="do not open up a CM ticket for this load",
    )
    parser.add_option(
        "--no-curses",
        action="store_true",
        help="do not use ncurses output; output everything line-by-line in a log format",
    )
    parser.add_option(
        "--auto",
        action="store_true",
        help="automatically proceed with loads; for use with cron; assumes -q",
    )

    opts, args = parser.parse_args(argv)

    if opts.escalation:
        opts.queue = True
    if opts.queue and opts.no_db:
        parser.error("Can't check load queue without database access")
    if opts.queue and opts.file:
        parser.error("Can't get ACL load plan from both queue and file")
    if len(args) == 1 and not opts.file and not opts.queue and not opts.auto:
        parser.print_help()
    if opts.auto:
        opts.quiet = True
    if opts.quiet:
        sys.stdout = NullDevice()
    if opts.bouncy:
        opts.jobs = 1
        print("Bouncy enabled, disabling multiple jobs.")
        log.msg("Bouncy enabled, disabling multiple jobs.")

    return opts, args


def debug_fakeout():
    """Used for debug, but this method is rarely used."""
    return os.getenv("DEBUG_FAKEOUT") is not None


def get_work(opts, args):
    """Determine the set of devices to load on, and what ACLs to load on
    each.  Processes extra CLI arguments to modify the work queue. Return a
    dictionary of ``{nodeName: set(acls)}``.

    :param opts:
        A dictionary-like object of CLI options

    :param args:
        A list of CLI arguments
    """
    # removing acl. assumption from files
    aclargs = set(
        args[1:],
    )  # set([x.startswith('acl.') and x[4:] or x for x in args[1:]])

    work = {}
    bulk_acls = get_bulk_acls()

    def add_work(dev_name, acls):
        """A closure for the purpose of adding/updating ACLS for a given device.
        """
        try:
            dev = nd[dev_name]
        except KeyError:
            sys.stderr.write(f"WARNING: device {dev_name} not found")
            return
        try:
            work[dev] |= set(acls)
        except KeyError:
            work[dev] = set(acls)

    # Get the initial list, from whatever source.
    if opts.file:
        for line in Path(opts.file).open():  # noqa: SIM115
            if len(line) == 0 or line[0].isspace():
                # Lines with leading whitespace are wrapped pasted "acl" output
                continue
            a = line.rstrip().split()
            try:
                if len(a) == 1:
                    add_work(a[0], aclargs)
                elif aclargs:
                    add_work(a[0], set(a[1:]) & aclargs)
                else:
                    add_work(a[0], a[1:])
            except KeyError as e:
                sys.stderr.write(f"Unknown router: {e}")
                log.err(f"Unknown router: {e}")
                sys.exit(1)
    elif opts.queue:
        all_sql_data = queue.list()

        # First check to make sure our AUTOLOAD_FILTER_THRESH are under control
        # if they are not add them to the AUTOLOAD_BLACKLIST.
        # Next check if acls are bulk acls and process them accordingly.
        thresh_counts = defaultdict(int)
        defaultdict(int)

        for router, acl in all_sql_data:
            if acl in settings.AUTOLOAD_FILTER_THRESH:
                thresh_counts[acl] += 1
                if thresh_counts[acl] >= settings.AUTOLOAD_FILTER_THRESH[acl]:
                    print("adding", router, acl, " to AUTOLOAD_BLACKLIST")
                    log.msg(f"Adding {acl} to AUTOLOAD_BLACKLIST")
                    settings.AUTOLOAD_BLACKLIST.append(acl)

        for router, acl in all_sql_data:
            if not aclargs or acl in aclargs:
                if opts.auto:
                    ## check autoload blacklist
                    if acl not in settings.AUTOLOAD_BLACKLIST:
                        add_work(router, [acl])
                    else:
                        filtered_acls.add(acl)
                else:
                    add_work(router, [acl])
    else:
        found = set()
        for dev in nd.all():
            intersection = dev.acls & aclargs
            if len(intersection):
                add_work(dev.nodeName, intersection)
                found |= intersection
        not_found = list(aclargs - found)
        if not_found:
            not_found.sort()
            sys.stderr.write("No devices found for {}\n".format(", ".join(not_found)))
            sys.exit(1)

    # Process --bulk.  Only if not --bouncy.
    if not opts.bouncy:
        work = process_bulk_loads(work, bulk_acls, force_bulk=opts.bulk)

    # Process --exclude.
    if opts.exclude:
        # print 'stuff'
        exclude = set(opts.exclude)
        for dev in work:
            for ex in exclude:
                if fnmatch.fnmatchcase(dev.nodeName, ex) or dev.nodeName.startswith(
                    ex + ".",
                ):
                    del work[dev]
                    break
        for dev, acls in work.items():
            acls -= exclude  # noqa: PLW2901
            if len(acls) == 0:
                del work[dev]

    # Check bounce windows, and filter or warn.
    now = datetime.datetime.now(tz=pytz.UTC)
    next_ok = dict([(dev, dev.next_ok("load-acl", now)) for dev in work])
    bouncy_devs = [dev for dev, when in next_ok.items() if when > now]
    if bouncy_devs:
        bouncy_devs.sort()
        print()
        if opts.bouncy:
            for dev in bouncy_devs:
                dev_acls = ", ".join(work[dev])
                print(f"Loading {dev_acls} OUT OF BOUNCE on {dev}")
                log.msg(f"Loading {dev_acls} OUT OF BOUNCE on {dev}")
        else:
            for dev in bouncy_devs:
                dev_acls = ", ".join(work[dev])
                print(
                    "Skipping {} on {} (window starts at {})".format(
                        dev_acls, dev.nodeName.split(".")[0], pretty_time(next_ok[dev]),
                    ),
                )
                log.msg(
                    "Skipping {} on {} (window starts at {})".format(
                        dev_acls, dev.nodeName.split(".")[0], pretty_time(next_ok[dev]),
                    ),
                )
                del work[dev]
            print("\nUse --bouncy to forcefully load on these devices anyway.")
        print

    # Display filtered acls
    for a in filtered_acls:
        print(f"{a} is in AUTOLOAD_BLACKLIST; not added to work queue.")
        log.msg(f"{a} is in AUTOLOAD_BLACKLIST; not added to work queue.")

    return work


def junoscript_cmds(acls_content, tftp_paths, dev):
    """Return a list of Junoscript commands to load the given ACLs, and a
    matching list of tuples (acls remaining, human-readable status message).

    :param acls:
        A collection of ACL names

    :param dev:
        A Juniper `~trigger.netdevices.NetDevice` object
    """
    xml = [Element("lock-configuration")]
    status = ["locking configuration"]

    for i, acl_content in enumerate(acls_content):
        lc = Element("load-configuration", action="replace", format="text")
        body = SubElement(lc, "configuration-text")
        body.text = acl_content
        xml.append(lc)
        status.append("loading ACL " + tftp_paths[i])  # acl)

    # Add the proper commit command
    xml.extend(dev.commit_commands)
    status.append("committing for " + ",".join(tftp_paths))  # acls))
    status.append("done for" + ",".join(tftp_paths))

    if debug_fakeout():
        xml = [Element("get-software-information")] * (len(status) - 1)

    return xml, status


def ioslike_cmds(tftp_paths, dev, opts):  # , nonce):
    """Return a list of IOS-like commands to load the given ACLs, and a matching
    list of tuples (acls remaining, human-readable status message).

    :param acls:
        A collection of ACL names

    :param dev:
        An IOS-like `~trigger.netdevices.NetDevice` object

    :param nonce:
        A nonce to use when staging the ACL file for TFTP
    """
    template_base = {
        "arista": "copy tftp://%s/%s system:/running-config\n",
        "cisco": "copy tftp://%s/%s system:/running-config\n",
        "dell": "copy tftp://%s/%s running-config\n",
        "brocade": "copy tftp run %s %s\n",
        "foundry": "copy tftp run %s %s\n",
        "force10": "copy tftp://%s/%s running-config\n",
    }

    template = template_base[dev.vendor.name]
    cmds = [
        template % (get_tftp_source(dev=dev, no_vip=opts.no_vip), path)
        for path in tftp_paths
    ]
    status = ["loading ACL " + path for path in tftp_paths]  # this will print more info

    # Add the proper write mem command
    cmds.extend(dev.commit_commands)
    status.append("saving config for " + ",".join(tftp_paths))  # acls))
    status.append("done for " + ",".join(tftp_paths))  # acls))

    if debug_fakeout():
        cmds = ["show ver"] * (len(status) - 1)

    return cmds, status


def group(dev):
    """Helper for select_next_device().  Uses name heuristics to guess whether
    devices are "together".  Based loosely upon naming convention that is not
    the "strictest". Expect to need to tweak this.!

    :param dev:
        The `~trigger.netdevices.NetDevice` object to try to group
    """
    # TODO(jathan): Make this pattern configurable globally.
    trimmer = re.compile("[0-9]*[a-z]+")  # allow for e.g. "36bit1"

    # Try to match on nodeName, and if we don't (such as if it's an IP
    # address), just skip grouping.
    match = trimmer.match(dev.nodeName)
    if not match or not dev.site:
        return dev.nodeName

    group_key = match.group()

    # FIXME(jathan): This is some hard-coded AOL-specific legacy stuff that
    # will probably work for most environments, but it's awfully presumptuous.
    if len(group_key) >= 4 and group_key[-1] not in ("i", "e"):
        group_key = group_key[:-1] + "X"

    return (dev.site, group_key)


def select_next_device(work, active):
    """Select another device for the active queue.  Don't select a device
    if there is another of that "group" already there.

    :param work:
        The work dictionary (device to acls)

    :param active:
        Dictionary mapping running devs to human-readable status
    """
    active_groups = set([group(dev) for dev in active])
    for dev in work:
        if group(dev) not in active_groups:
            return dev
    return None


def clear_load_queue(dev, acls):
    """Logical wrapper around queue.complete(dev, acls)."""
    if debug_fakeout():
        return
    queue.complete(dev, acls)


def activate(work, active, failures, jobs, redraw, opts):
    """Refill the active work queue based on number of current active jobs.

    :param work:
        The work dictionary (device to acls)

    :param active:
        Dictionary mapping running devs to human-readable status

    :param failures:
        Dictionary of failures

    :param jobs:
        The max number of jobs for active queue

    :param redraw:
        The redraw closure passed along from the caller
    """
    if not active and not work and reactor.running:
        reactor.stop()

    while work and len(active) < jobs:
        dev = select_next_device(work, active)
        if not dev:
            break
        acls = work[dev]
        del work[dev]

        sanitize_acl = dev.vendor == "brocade"

        # Closures galore! Careful; you need to explicitly save current
        # values (using the default argument trick) 'dev', 'acls', and
        # 'status', because they vary through this loop.
        def update_board(results, dev, status):
            with contextlib.suppress(IndexError):
                active[dev] = status[len(results)]

        def complete(results, dev, acls):
            if queue:
                clear_load_queue(dev, acls)

        def eb(reason, dev):
            log.msg("GOT ERRBACK", reason)
            failures[dev] = reason

        def move_on(x, dev):
            del active[dev]
            activate(work, active, failures, jobs, redraw, opts)

        def stage_acls_cb(unused, dev, acls, log, sanitize_acl):
            # Wrapper for stage_acls; result is unused
            active[dev] = "staging acls"
            return stage_acls(acls, log, sanitize_acl)

        def check_failure(result, dev):
            (acl_contents, tftp_paths, fails) = result

            if fails:
                log.msg("STAGING FAILED:", fails)
                raise exceptions.ACLStagingFailed(fails)

            active[dev] = "connecting"
            if dev.vendor == "juniper":
                cmds, status = junoscript_cmds(acl_contents, tftp_paths, dev)
            else:
                cmds, status = ioslike_cmds(tftp_paths, dev, opts)

            return (cmds, status)

        # Stage the acls
        handled_first = defer.Deferred()
        handled_first.addCallback(stage_acls_cb, dev, acls, log, sanitize_acl)
        handled_first.addBoth(check_failure, dev)
        handled_first.addErrback(eb, dev)
        handled_first.addErrback(move_on, dev)

        # Start staging
        reactor.callWhenRunning(handled_first.callback, None)

        def chain(result, dev, acls):
            (cmds, status) = result

            # Lambda function to call update_board() with proper args
            def incremental(x):
                return update_board(x, dev, status)

            if dev.vendor in ("brocade", "foundry"):
                handled_second = dev.execute(
                    cmds, incremental=incremental, command_interval=1,
                )
            else:
                handled_second = dev.execute(cmds, incremental=incremental)
            handled_second.addCallback(complete, dev, acls)
            handled_second.addErrback(eb, dev)
            handled_second.addBoth(move_on, dev)

        # Try to actually push the changes after staging completes successfully
        handled_first.addCallback(chain, dev, acls)

        redraw()


def run(stdscr, work, jobs, failures, opts):
    """Runs the show. Starts the curses status board & starts the reactor loop.

    :param stdscr:
        The starting curses screen (usually None)

    :param work:
        The work dictionary (device to acls)

    :param jobs:
        The max number of jobs for active queue

    :param failures:
        Dictionary of failures
    """
    # Dictionary of currently running devs -> human-readable status
    active = {}

    start_qlen = len(work)
    start_time = time.time()

    def redraw():
        """A closure to redraw the screen with current environment."""
        draw_screen(stdscr, work, active, failures, start_qlen, start_time)

    activate(work, active, failures, jobs, redraw, opts)

    # Make sure the screen is updated regularly even when nothing happens.
    drawloop = task.LoopingCall(redraw)
    drawloop.start(0.25)

    reactor.run()


def main():
    """The Main Event."""
    global opts
    opts, args = parse_args(sys.argv)

    if opts.severed_head:
        print_severed_head()
        sys.exit(0)
    if opts.auto:
        opts.no_curses = True
        opts.queue = True

    global queue
    if opts.no_db:
        queue = None

    if (not opts.auto) or (not opts.quiet):
        print("Logging to", tmpfile)

    # Where the magic happens
    work = get_work(opts, args)

    if not work:
        if not opts.auto:
            print("Nothing to load.")
        log.msg("Nothing to load.")
        sys.exit(0)

    print("You are about to perform the following loads:")
    print()
    devs = work.items()
    devs.sort()
    for dev, acls in devs:
        acls = list(work[dev])  # noqa: PLW2901
        acls.sort()
        print("%-32s %s" % (dev, " ".join(acls)))
    acl_count = len(acls)
    print()
    if debug_fakeout():
        print("DEBUG FAKEOUT ENABLED")
        failures = {}
        run(None, work, opts.jobs, failures, opts)
        sys.exit(1)

    if not opts.auto:
        if opts.bouncy:
            print(
                "NOTE: Parallel jobs disabled for out of bounce loads, this will take longer than usual.",
            )
            print()

        confirm = input("Are you sure you want to proceed? ")
        if not confirm.lower().startswith("y"):
            print("LOAD CANCELLED")
            log.msg("LOAD CANCELLED")
            sys.exit(1)
        print()
        # Don't let the credential prompts get hidden behind curses
        Tacacsrc()
    else:
        log.msg("Auto option thrown, checking if credential file exists")
        tacacsrc_file = settings.TACACSRC
        if not Path(tacacsrc_file).exists():
            log.msg(f"No {tacacsrc_file} file exists and auto option enabled.")
            sys.exit(1)
        log.msg(f"Credential file {tacacsrc_file} exists, moving on")

    cm_ticketnum = 0
    if not opts.no_cm and not debug_fakeout():
        oncall = get_current_oncall()
        if not oncall:
            if opts.auto:
                send_notification(
                    "LOAD_ACL FAILURE", "Unable to get current ON-CALL information!",
                )
            log.err("Unable to get on-call information!", logLevel=logging.CRITICAL)
            sys.exit(1)

        print("\nSubmitting CM ticket...")
        # catch failures to create a ticket
        try:
            cm_ticketnum = create_cm_ticket(work, oncall)
        except:
            # create_cm_ticket is user defined
            # so we don't know what exceptions can be returned
            cm_ticketnum = None
        if not cm_ticketnum:
            es = "Unable to create CM ticket!"
            if opts.auto:
                send_notification("LOAD_ACL FAILURE", es)
            log.err(es, logLevel=logging.CRITICAL)
            sys.exit(es)

        cm_msg = f"Created CM ticket #{cm_ticketnum}"
        print(cm_msg)
        log.msg(cm_msg)

    start = time.time()
    # Dicionary of failures and their causes
    failures = {}

    # Don't use curses.wrapper(), because that initializes colors which
    # means that we won't be using the user's chosen colors.  Default in
    # an xterm is ugly gray on black, not black on white.  We can't even
    # fix it since white background becomes unavailable.
    stdscr = None
    try:
        if not opts.no_curses:
            stdscr = curses.initscr()
            stdscr.idlok(1)
            stdscr.scrollok(0)
            curses.noecho()
        run(stdscr, work, opts.jobs, failures, opts)
    finally:
        if not opts.no_curses:
            curses.echo()
            curses.endwin()

    failed_count = 0
    for dev, reason in failures.items():
        failed_count += 1
        log.err(f"LOAD FAILED ON {dev}: {reason!s}")
        sys.stderr.write(f"LOAD FAILED ON {dev}: {reason!s}")

    if failures and not opts.auto:
        print_severed_head()

    if opts.auto:
        if failed_count:
            send_notification(
                "LOAD_ACL FAILURE",
                "%d ACLS failed to load! See logfile: %s on jumphost."
                % (failed_count, tmpfile),
            )
        else:
            send_email(
                settings.SUCCESS_EMAILS,
                "LOAD ACL SUCCESS!",
                "%d acls loaded successfully! see log file: %s" % (acl_count, tmpfile),
                settings.EMAIL_SENDER,
            )

    log.msg("%d failures" % failed_count)
    log.msg(f"Elapsed time: {min_sec(time.time() - start)}")


if __name__ == "__main__":
    fd, tmpfile = tempfile.mkstemp(suffix="_load_acl")
    log.startLogging(os.fdopen(fd, "a"), setStdout=False)
    log.msg(
        'User %s (uid:%d) executed "%s"'
        % (os.environ["LOGNAME"], os.getuid(), " ".join(sys.argv)),
    )
    main()
