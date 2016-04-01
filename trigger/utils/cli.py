#coding=utf-8

"""
Command-line interface utilities for Trigger tools. Intended for re-usable
pieces of code like user prompts, that don't fit in other utils modules.
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2006-2012, AOL Inc.; 2013 Salesforce.com'

import datetime
from fcntl import ioctl
import os
import pwd
from pytz import timezone, UTC
import struct
import sys
import termios
import time
import tty

# Exports
__all__ = ('yesno', 'get_terminal_width', 'get_terminal_size', 'Whirlygig',
           'NullDevice', 'print_severed_head', 'min_sec', 'pretty_time',
           'proceed', 'get_user')


# Functions
def yesno(prompt, default=False, autoyes=False):
    """
    Present a yes-or-no prompt, get input, and return a boolean.

    The ``default`` argument is ignored if ``autoyes`` is set.

    :param prompt:
        Prompt text

    :param default:
        Yes if True; No if False

    :param autoyes:
        Automatically return True

    Default behavior (hitting "enter" returns ``False``)::

        >>> yesno('Blow up the moon?')
        Blow up the moon? (y/N)
        False

    Reversed behavior (hitting "enter" returns ``True``)::

        >>> yesno('Blow up the moon?', default=True)
        Blow up the moon? (Y/n)
        True

    Automatically return ``True`` with ``autoyes``; no prompt is displayed::

        >>> yesno('Blow up the moon?', autoyes=True)
        True
    """
    if autoyes:
        return True

    sys.stdout.write(prompt)
    if default:
        sys.stdout.write(' (Y/n) ')
    else:
        sys.stdout.write(' (y/N) ')
    sys.stdout.flush()

    fd = sys.stdin.fileno()
    attr = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        yn = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, attr)
        print ''

    if yn in ('y', 'Y'):
        return True
    elif yn in ('n', 'N'):
        return False
    else:
        return default

def proceed():
    """Present a proceed prompt. Return ``True`` if Y, else ``False``"""
    return raw_input('\nDo you wish to proceed? [y/N] ').lower().startswith('y')

def get_terminal_width():
    """Find and return stdout's terminal width, if applicable."""
    try:
        width = struct.unpack("hhhh", ioctl(1, termios.TIOCGWINSZ, ' '*8))[1]
    except IOError:
        width = sys.maxint

    return width

def get_terminal_size():
    """Find and return stdouts terminal size as (height, width)"""
    rows, cols = os.popen('stty size', 'r').read().split()
    return rows, cols

def get_user():
    """Return the name of the current user."""
    return pwd.getpwuid(os.getuid())[0]

def print_severed_head():
    """
    Prints a demon holding a severed head. Best used when things go wrong, like
    production-impacting network outages caused by fat-fingered ACL changes.

    Thanks to Jeff Sullivan for this best error message ever.
    """
    print r"""

                                                                _( (~\
         _ _                        /                          ( \> > \
     -/~/ / ~\                     :;                \       _  > /(~\/
    || | | /\ ;\                   |l      _____     |;     ( \/    > >
    _\\)\)\)/ ;;;                  `8o __-~     ~\   d|      \      //
   ///(())(__/~;;\                  "88p;.  -. _\_;.oP        (_._/ /
  (((__   __ \\   \                  `>,% (\  (\./)8"         ;:'  i
  )))--`.'-- (( ;,8 \               ,;%%%:  ./V^^^V'          ;.   ;.
  ((\   |   /)) .,88  `: ..,,;;;;,-::::::'_::\   ||\         ;[8:   ;
   )|  ~-~  |(|(888; ..``'::::8888oooooo.  :\`^^^/,,~--._    |88::  |
   |\ -===- /|  \8;; ``:.      oo.8888888888:`((( o.ooo8888Oo;:;:'  |
   |_~-___-~_|   `-\.   `        `o`88888888b` )) 888b88888P""'     ;
   ; ~~~~;~~         "`--_`.       b`888888888;(.,"888b888"  ..::;-'
     ;      ;              ~"-....  b`8888888:::::.`8888. .:;;;''
        ;    ;                 `:::. `:::OOO:::::::.`OO' ;;;''
   :       ;                     `.      "``::::::''    .'
      ;                           `.   \_              /
    ;       ;                       +:   ~~--  `:'  -';    ACL LOADS FAILED
                                     `:         : .::/
        ;                            ;;+_  :::. :..;;;         YOU LOSE
                                     ;;;;;;,;;;;;;;;,;

"""

def pretty_time(t):
    """
    Print a pretty version of timestamp, including timezone info. Expects
    the incoming datetime object to have proper tzinfo.

    :param t:
        A ``datetime.datetime`` object

    >>> import datetime
    >>> from pytz import timezone
    >>> localzone = timezone('US/Eastern')
    <DstTzInfo 'US/Eastern' EST-1 day, 19:00:00 STD>
    >>> t = datetime.datetime.now(localzone)
    >>> print t
    2011-07-19 12:40:30.820920-04:00
    >>> print pretty_time(t)
    09:40 PDT
    >>> t = localzone.localize(datetime.datetime(2011,07,20,04,13))
    >>> print t
    2011-07-20 04:13:00-05:00
    >>> print pretty_time(t)
    tomorrow 02:13 PDT
    """
    from trigger.conf import settings
    localzone = timezone(os.environ.get('TZ', settings.BOUNCE_DEFAULT_TZ))
    t = t.astimezone(localzone)
    ct = t.replace(tzinfo=None) # convert to naive time
    # to make the following calculations easier
    # calculate naive 'now' in local time
    # passing localzone into datetime.now directly can cause
    # problems, see the 'pytz' docs if curious
    now = datetime.datetime.now(UTC)
    now = now.astimezone(localzone)
    now = now.replace(tzinfo=None)
    # and compute midnight
    midnight = datetime.datetime.combine(now, datetime.time())
    midnight += datetime.timedelta(1)
    tomorrow = midnight + datetime.timedelta(1)
    thisweek = midnight + datetime.timedelta(6)
    if ct < midnight:
        return t.strftime('%H:%M %Z')
    elif ct < tomorrow:
        return t.strftime('tomorrow %H:%M %Z')
    elif ct < thisweek:
        return t.strftime('%A %H:%M %Z')
    else:
        return t.strftime('%Y-%m-%d %H:%M %Z')

def min_sec(secs):
    """
    Takes an epoch timestamp and returns string of minutes:seconds.

    :param secs:
        Timestamp (in seconds)

    >>> import time
    >>> start = time.time()  # Wait a few seconds
    >>> finish = time.time()
    >>> min_sec(finish - start)
    '0:11'
    """
    secs = int(secs)
    return '%d:%02d' % (secs / 60, secs % 60)

def setup_tty_for_pty(func):
    """
    Sets up tty for raw mode while retaining original tty settings and then
    starts the reactor to connect to the pty. Upon exiting pty, restores
    original tty settings.

    :param func:
        The callable to run after the tty is ready, such as ``reactor.run``
    """
    # Preserve original tty settings
    stdin_fileno = sys.stdin.fileno()
    old_ttyattr = tty.tcgetattr(stdin_fileno)

    try:
        # Enter raw mode on the local tty.
        tty.setraw(stdin_fileno)
        raw_ta = tty.tcgetattr(stdin_fileno)
        raw_ta[tty.LFLAG] |= tty.ISIG
        raw_ta[tty.OFLAG] |= tty.OPOST | tty.ONLCR

        # Pass ^C through so we can abort traceroute, etc.
        raw_ta[tty.CC][tty.VINTR] = '\x18'  # ^X is the new ^C

        # Ctrl-Z is used by a lot of vendors to exit config mode
        raw_ta[tty.CC][tty.VSUSP] = 0       # disable ^Z
        tty.tcsetattr(stdin_fileno, tty.TCSANOW, raw_ta)

        # Execute our callable here
        func()

    finally:
        # Restore original tty settings
        tty.tcsetattr(stdin_fileno, tty.TCSANOW, old_ttyattr)

def update_password_and_reconnect(hostname):
    """
    Prompts the user to update their password and reconnect to the target
    device

    :param hostname: Hostname of the device to connect to.
    """
    if yesno('Authentication failed, would you like to update your password?',
             default=True):
        from trigger import tacacsrc
        tacacsrc.update_credentials(hostname)
        if yesno('\nReconnect to %s?' % hostname, default=True):
            # Replaces the current process w/ same pid
            args = [sys.argv[0]]
            for arg in ('-o', '--oob'):
                if arg in sys.argv:
                    idx = sys.argv.index(arg)
                    args.append(sys.argv[idx])
                    break
            args.append(hostname)
            os.execl(sys.executable, sys.executable, *args)

# Classes
class NullDevice(object):
    """
    Used to supress output to ``sys.stdout`` (aka ``print``).

    Example::

        >>> from trigger.utils.cli import NullDevice
        >>> import sys
        >>> print "1 - this will print to STDOUT"
        1 - this will print to STDOUT
        >>> original_stdout = sys.stdout  # keep a reference to STDOUT
        >>> sys.stdout = NullDevice()     # redirect the real STDOUT
        >>> print "2 - this won't print"
        >>>
        >>> sys.stdout = original_stdout  # turn STDOUT back on
        >>> print "3 - this will print to SDTDOUT"
        3 - this will print to SDTDOUT
    """
    def write(self, s): pass

class Whirlygig(object):
    """
    Prints a whirlygig for use in displaying pending operation in a command-line tool.
    Guaranteed to make the user feel warm and fuzzy and be 1000% bug-free.

    :param start_msg: The status message displayed to the user (e.g. "Doing stuff:")
    :param done_msg: The completion message displayed upon completion (e.g. "Done.")
    :param max: Integer of the number of whirlygig repetitions to perform

    Example::

        >>> Whirlygig("Doing stuff:", "Done.", 12).run()
    """

    def __init__(self, start_msg="", done_msg="", max=100):
        self.unbuff = os.fdopen(sys.stdout.fileno(), 'w', 0)
        self.start_msg = start_msg
        self.done_msg = done_msg
        self.max = max
        self.whirlygig = ['|', '/', '-', '\\']
        self.whirl    = self.whirlygig[:]
        self.first = False

    def do_whirl(self, whirl):
        if not self.first:
            self.unbuff.write(self.start_msg + "  ")
            self.first = True
        self.unbuff.write('\b%s' % whirl.pop(0))

    def run(self):
        """Executes the whirlygig!"""
        cnt = 1
        while cnt <= self.max:
            try:
                self.do_whirl(self.whirl)
            except IndexError:
                self.whirl = self.whirlygig[:]
            time.sleep(.1)
            cnt += 1
        print '\b' + self.done_msg
