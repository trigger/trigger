#coding=utf-8

"""
Command-line interface utilities for Trigger tools. Intended for re-usable
pieces of code like user prompts, that don't fit in other utils modules.
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2006-2011, AOL Inc.'

import datetime
from fcntl import ioctl
import os
from pytz import timezone
import struct
import sys
import termios
import time
import tty


# Exports
__all__ = ('yesno', 'get_terminal_width', 'get_terminal_size', 'Whirlygig',
           'NullDevice', 'print_severed_head', 'min_sec', 'pretty_time')


# Functions
def yesno(prompt, default=False):
    """
    Present a yes-or-no prompt, get input, and return a boolean.

    :param prompt: Prompt text
    :param default: Yes if True; No if False
    """
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
    """Present a proceed prompt. Return True if Y, else False."""
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

def print_severed_head():
    '''Thanks to Jeff Sullivan for this best error message ever.'''
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

    >>> import datetime
    >>> from pytz import timezone
    >>> localzone = timezone('US/Eastern')
    <DstTzInfo 'US/Eastern' EST-1 day, 19:00:00 STD>
    >>> t = datetime.datetime.now(localzone)
    >>> print t
    2011-07-19 12:40:30.820920-04:00
    >>> print pretty_time(t)
    09:40 PDT
    >>> t = datetime.datetime(2011,07,20,04,13,tzinfo=localzone)
    >>> print t
    2011-07-20 04:13:00-05:00
    >>> print pretty_time(t)
    tomorrow 02:13 PDT
    """
    localzone = timezone(os.environ.get('TZ', 'US/Eastern'))
    t = t.astimezone(localzone)
    midnight = datetime.datetime.combine(datetime.datetime.now(), datetime.time(tzinfo=localzone))
    midnight += datetime.timedelta(1)
    if t < midnight:
        return t.strftime('%H:%M %Z')
    elif t < midnight + datetime.timedelta(1):
        return t.strftime('tomorrow %H:%M %Z')
    elif t < midnight + datetime.timedelta(6):
        return t.strftime('%A %H:%M %Z')
    else:
        return t.strftime('%Y-%m-%d %H:%M %Z')

def min_sec(secs):
    """Takes epoch timestamp and returns string of minutes:seconds."""
    secs = int(secs)
    return '%d:%02d' % (secs / 60, secs % 60)

# Classes
class NullDevice(object):
    """
    Used to supress output to sys.stdout.

    Example:

    print "1 - this will print to STDOUT"
    original_stdout = sys.stdout  # keep a reference to STDOUT
    sys.stdout = NullDevice()  # redirect the real STDOUT
    print "2 - this won't print"
    sys.stdout = original_stdout  # turn STDOUT back on
    print "3 - this will print to SDTDOUT"
    """
    def write(self, s): pass

class Whirlygig(object):
    """
    Prints a whirlygig for use in displaying pending operation in a command-line tool.
    Guaranteed to make the user feel warm and fuzzy and be 1000% bug-free.

    :param start_msg: The status message displayed to the user (e.g. "Doing stuff:")
    :param done_msg: The completion message displayed upon completion (e.g. "Done.")
    :param max: Integer of the number of whirlygig repetitions to perform

    Example:
        >>> Whirly("Doing stuff:", "Done.", 12).run()
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
