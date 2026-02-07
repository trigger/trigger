#!/usr/bin/env python

"""Do It (Next Generation).

Uses Trigger framework to run commands or load configs on netdevices

This is the base module called by front-end scripts.

main() is never actually called from within here, and takes a single argument
the docommand class that needs to be instanced.

This base function exists so that tools using the module can maintain a consistent
usability for arguments and output.

Scripts using this module are passed CLI arguments specifying the device(s) and
command(s)/configuration line(s) desired to run/load.

The list of devices and configuration lines may be specified either directly on
the commandline (comma-separated values) or by specifying files containing these
lists. Any files containing configs *must* be located in a tftp directory.
Configs specified on commandline will either be written to a tftp directory in a
tmp file (future) or run directly on the devices (current)

Please see --help for details on how to construct your arguments

(not yet supported)
--device-path arg to specify directory containing configs.
Each file would be named as the devname and
contents would be the config you want loaded to that specific device.
**waiting on enhancements to Commando for implementation**

(not yet supported)
--match arg to allow matching on netdevices.xml fields to compile list of devices
**not waiting on anything, just not implemented in v1**
"""

__author__ = "Jathan McCollum, Mike Biancianello"
__maintainer__ = "Jathan McCollum"
__email__ = "jathan@gmail.com"
__copyright__ = "Copyright 2012-2013, AOL Inc.; 2013-2014, Salesforce.com"
__version__ = "3.1.1"


# Imports
import os
import re
import sys
import tempfile
from optparse import OptionParser
from pathlib import Path

from twisted.python import log

# Globals
PROD_ONLY = False
DEBUG = False
VERBOSE = False
PUSH = False
FORCE_CLI = False
TIMEOUT = 30


# Exports
__all__ = (
    "do_work",
    "get_commands_from_opts",
    "get_devices_from_opts",
    "get_devices_from_path",
    "get_jobs",
    "get_list_from_file",
    "main",
    "parse_args",
    "print_results",
    "print_work",
    "set_globals_from_opts",
    "stage_tftp",
    "verify_opts",
)


# Functions
def main(action_class=None):
    """Run the docommand main entry point with the given action class."""
    if action_class is None:
        sys.exit("You must specify a docommand action class.")

    if os.getenv("DEBUG"):
        log.startLogging(sys.stdout, setStdout=False)

    # Always log all the activity to a file!
    fd, _logfile = tempfile.mkstemp(suffix="_run_cmds")
    log.startLogging(os.fdopen(fd, "a"), setStdout=False)
    log.msg(
        'User %s (uid:%d) executed "%s"'
        % (os.environ["LOGNAME"], os.getuid(), " ".join(sys.argv)),
    )

    # Description comes from a class attribute on the action_class
    opts, _args = parse_args(sys.argv, description=action_class.description)
    work = get_jobs(opts)
    results = do_work(work, action_class)
    print_results(results)
    print("\nDone.")


def get_jobs(opts):
    """Build a list of jobs from the given options.

    Based on which arguments are provided, figure out what is loaded/run on
    which devices and create a list of objects matching the 2::

        job = {'d': [],'c': [],'f': []}

    Is read as "load ALL configs listed in 'c' on ALL devs listed in 'd'". Each
    such grouping is a separate job.

    Future enhancements:

    + If multiple jobs exist for the same device we should regroup and optimize
      biggest optimization, though, will come after minor Commando enhancements
      would allow feeding entire list into a single run()
    """
    if DEBUG:
        print(f"-->get_jobs({opts!r})")
    work = []
    if opts.device_path:
        # If using device-path, then each device gets a customized list of
        # commands so we have to iterate over the devices and call Commando for
        # each device.
        path = opts.device_path
        if VERBOSE:
            print(f"getting devicelist from path: {path}")

        # Normalize path variable
        if not re.search("/$", path):
            path = path + "/"
        devs = get_devices_from_path(path)

        if VERBOSE:
            print(f"\tfound {len(devs)} devices")

        for dev in devs:
            cmds = []
            files = [path + dev]
            job = {"d": [dev], "c": cmds, "f": files}
            work.append(job)
    else:
        # If not using device-path, then devs and cmds are referenced on the
        # cmdline.
        devs = get_devices_from_opts(opts)
        cmds = opts.config
        files = opts.config_file
        work = [{"d": devs, "c": cmds, "f": files}]
    return work


def get_devices_from_path(path):
    """Return device names from filenames in the given directory path.

    If path specified for devices/configs, then the list of filenames
    in dir will correspond to the list of devices.

    The contents of each file contain the config/commands to be loaded/run
    on the specific device.

    Future enhancements

    + verify that the filenames are fqdns
    + verify that the devnames exist in netdevices.xml
    """
    if DEBUG:
        print(f"-->get_devices_from_path({path!r})")

    return [p.name for p in Path(path).iterdir()]


def get_list_from_file(path):
    """Read newline-separated items from a file and return as a list.

    Specified file (path) will contain a list of newline-separated items. This
    function is used for loading both configs/cmds as well as devices.
    """
    if DEBUG:
        print(f"-->get_list_from_file({path!r})")
    ret = []
    with Path(path).open() as fr:
        ret = fr.readlines()
    return [x.strip() for x in ret]


def get_devices_from_opts(opts):
    """Return device names from command-line options.

    User specified on cmdline either a path to a file containing a list of
    devices or an actual list. Return the list!
    """
    if DEBUG:
        print(f"-->get_devices_from_opts({opts!r})")
    ret = []
    if len(opts.device_file) > 0:
        ret = []
        for df in opts.device_file:
            devlist = get_list_from_file(df)
            for dev in devlist:
                ret.append(dev)
    else:
        ret = opts.devices
    if VERBOSE:
        print(f"loaded {len(ret)} devices")
    if DEBUG:
        print(f"ret: {ret}")
    return ret


def get_commands_from_opts(opts):
    """Return commands from command-line options.

    User specified on cmdline either a path to a file containing a list of
    commands/config or an actual list. Return the list!
    """
    if DEBUG:
        print(f"-->get_commands_from_opts({opts!r})")
    ret = []
    if len(opts.config_file) > 0:
        ret = []
        for cf in opts.config_file:
            cmdlist = get_list_from_file(cf)
            for cmd in cmdlist:
                ret.append(cmd)
    else:
        ret = opts.config
    if VERBOSE:
        print(f"loaded {len(ret)} commands")
    return ret


def do_work(work=None, action_class=None):
    """Cycle through the list of jobs and execute them on devices."""
    if work is None:
        work = []
    if DEBUG:
        print(f"-->do_work({work!r})")
    ret = []
    if VERBOSE:
        print_work(work)
    for job in work:
        f = job["f"]
        d = job["d"]
        c = job["c"]

        # **These next 2 lines do all the real work for this tool**
        # TODO: This will ultimately fail with a ReactorNotRestartable because
        # calling each action class separately. We need to account for this.
        # See: https://gist.github.com/jathanism/4543974
        n = action_class(
            devices=d,
            files=f,
            commands=c,
            verbose=VERBOSE,
            debug=DEBUG,
            timeout=TIMEOUT,
            production_only=PROD_ONLY,
            force_cli=FORCE_CLI,
        )

        if PUSH:
            if VERBOSE:
                print("running Commando")
            n.run()
        else:
            print("*** Dry-run mode; Skipping command execution***")
        for devname in n.data:
            data = n.data[devname]
            res = {"devname": devname, "data": data}
            ret.append(res)
        del n
    return ret


def print_work(work=None):
    """Void = do_work(list work).

    Cycle through the list of jobs and then display the work to be done.
    """
    if work is None:
        work = []
    if DEBUG:
        print(f"-->print_work({work!r})")

    for i, job in enumerate(work):
        print("\n***JOB %s ***" % (i + 1))
        f = job["f"]
        d = job["d"]
        c = job["c"]

        if len(d) > 0:
            print("\tDevices")
            for dev in d:
                print("\t\t" + dev)

        if len(f) > 0:
            print("\tLoad From Files:")
            for file in f:
                print("\t\t" + file)

        if len(c) > 0:
            print("\tRun Commands:")
            for cmd in c:
                print("\t\t" + cmd)

    return True


def print_results(results=None):
    """Print formatted results from completed jobs."""
    if results is None:
        results = []
    if DEBUG:
        print(f"-->print_results({results!r})")
    for res in results:
        devname = res["devname"]
        data = res["data"]
        print()
        print("###")
        print(f"# {devname}")
        print("###")
        for d in data:
            cmd = d["cmd"]
            out = d["out"]
            device = d["dev"]
            print(
                f"{device.shortName}# {cmd}\n{out}",
            )
    return True


def stage_tftp(acls, nonce):
    """Need to edit this for cmds, not just acls, but
    the basic idea is borrowed from ``bin/load_acl``.
    """
    for _device in devices:
        source = settings.FIREWALL_DIR + f"/acl.{acl}"
        dest = settings.TFTPROOT_DIR + f"/acl.{acl}.{nonce}"
        try:
            Path(dest).stat()
        except OSError:
            try:
                copyfile(source, dest)
                Path(dest).chmod(0o644)
            except:
                return None
    return True


def parse_args(argv, description=None):
    if description is None:
        description = "insert description here."

    def comma_cb(option, opt_str, value, parser):
        """OptionParser callback to handle comma-separated arguments."""
        values = value.split(",")  # Split on commas
        values = [v.strip() for v in values]  # Strip trailing space from values
        try:
            getattr(parser.values, option.dest).extend(values)
        except AttributeError:
            setattr(parser.values, option.dest, values)

    parser = OptionParser(
        usage="%prog [options]",
        description=description,
        version=__version__,
    )
    # Options to collect lists of devices and commands
    parser.add_option(
        "-d",
        "--devices",
        type="string",
        action="callback",
        callback=comma_cb,
        default=[],
        help="Comma-separated list of devices.",
    )
    parser.add_option(
        "-c",
        "--config",
        type="string",
        action="callback",
        callback=comma_cb,
        default=[],
        help="Comma-separated list of config statements.  "
        'If your commands have spaces, either enclose the command in " or escape the '
        "spaces with \\",
    )
    parser.add_option(
        "-D",
        "--device-file",
        type="string",
        action="callback",
        callback=comma_cb,
        default=[],
        help="Specify file with list of devices.",
    )
    parser.add_option(
        "-C",
        "--config-file",
        type="string",
        action="callback",
        callback=comma_cb,
        default=[],
        help="Specify file with list of config statements.  "
        "The file MUST be in a tftp directory (/home/tftp/<subdir>). "
        "The fully-qualified path MUST be specified in the argument. "
        'Do NOT include "conf t" or "wr mem" in your file. '
        "** If both -c and -C options specified, then -c will execute first, followed by -C",
    )
    parser.add_option(
        "-p",
        "--device-path",
        type="string",
        default=None,
        help="Specify dir with a file named for each device. "
        "Contents of each file must be list of commands. "
        "that you want to run for the device that shares its name with the file. "
        "** May NOT be used with -d,-c,-D,-C **",
    )
    parser.add_option(
        "-q",
        "--quiet",
        action="store_true",
        help="suppress all standard output; errors/warnings still display.",
    )
    """
    parser.add_option('--exclude', '--except', type='string',
                      action='callback', callback=comma_cb, dest='exclude',
                      default=[],
                      help='***NOT YET IMPLEMENTED***  '
                           'skip over devices; shell-type patterns '
                           '(e.g., "edge?-[md]*") can be used for devices; for '
                           'multiple excludes, use commas or give this option '
                           'more than once.')
    """
    parser.add_option(
        "-j",
        "--jobs",
        type="int",
        default=5,
        help="maximum simultaneous connections (default 5).",
    )
    parser.add_option(
        "-t",
        "--timeout",
        type="int",
        default=TIMEOUT,
        help=f"""Time in seconds to wait for each command to
                      complete (default {TIMEOUT}).""",
    )
    # Booleans below
    parser.add_option(
        "-f",
        "--force-cli",
        action="store_true",
        default=False,
        help="Force CLI execution, skipping the API.",
    )
    parser.add_option(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="verbose output.",
    )
    parser.add_option(
        "-V",
        "--debug",
        action="store_true",
        default=False,
        help="debug output.",
    )
    parser.add_option(
        "--push",
        action="store_true",
        default=False,
        help="actually do stuff.  Default is False.",
    )

    opts, args = parser.parse_args(argv)

    # Validate option logic
    ok, err = verify_opts(opts)
    if not ok:
        print("\n", err)
        sys.exit(1)
    if opts.quiet:
        sys.stdout = NullDevice()

    # Mutate some global sentinel values based on opts
    set_globals_from_opts(opts)

    return opts, args


def verify_opts(opts):
    """Validate opts and return whether they are ok.

    returns True if all is good, otherwise (False, errormsg)
    """
    ok = True
    err = ""
    isd = len(opts.devices) > 0
    isc = len(opts.config) > 0
    isdf = len(opts.device_file) > 0
    iscf = len(opts.config_file) > 0
    isp = opts.device_path is not None
    if isp:
        if not Path(opts.device_path).is_dir():
            return False, f"ERROR: {opts.device_path!r} is not a valid directory\n"
        return True, ""
    if isdf or iscf or isd or isc:
        pass

    # Validate opts.device_file
    if isdf:
        for df in opts.device_file:
            if not Path(df).exists():
                ok = False
                err += f"ERROR: Device file {df!r} does not exist\n"

    # Validate opts.config_file
    if iscf:
        for cf in opts.config_file:
            if not Path(cf).exists():
                ok = False
                err += f"ERROR: Config file {cf!r} does not exist\n"

    # If opts.devices is set, opts.device_file must also be set
    if not isd and not isdf:
        ok = False
        err += "ERROR: You must specify at least one device\n"
    # If opts.config is set, opts.config_file must also be set
    if not isc and not iscf:
        ok = False
        err += "ERROR: You must specify at least one command\n"

    # TODO: One option here would be to take opts.config, write to file, and
    # convert that to opts.config_file. That way, the rest of the script only
    # has to care about one type of input.
    return ok, err


# TODO: There's gotta be a better way.
def set_globals_from_opts(opts):
    global DEBUG
    global VERBOSE
    global PUSH
    global TIMEOUT
    global FORCE_CLI
    DEBUG = opts.debug
    VERBOSE = opts.verbose
    PUSH = opts.push
    TIMEOUT = opts.timeout
    FORCE_CLI = opts.force_cli
