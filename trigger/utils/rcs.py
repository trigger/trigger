#coding=utf-8

"""
Provides a CVS like wrapper for local RCS (Revision Control System) with common commands.
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2009-2011, AOL Inc.'

import commands
import os
import time


# Exports
__all__ = ('RCS',)


# Classes
class RCS(object):
    """
    Simple wrapper for CLI ``rcs`` command. An instance is bound to a file.

    :param file: The filename (or path) to use
    :param create: If set, create the file if it doesn't exist

    >>> from trigger.utils.rcs import RCS
    >>> rcs = RCS('foo')
    >>> rcs.lock()
    True
    >>> f = open('foo', 'w')
    >>> f.write('bar\\n')
    >>> f.close()
    >>> rcs.checkin('This is my commit message')
    True
    >>> print rcs.log()
    RCS file: RCS/foo,v
    Working file: foo
    head: 1.2
    branch:
    locks: strict
    access list:
    symbolic names:
    keyword substitution: kv
    total revisions: 2;     selected revisions: 2
    description:
    ----------------------------
    revision 1.2
    date: 2011/07/08 21:01:28;  author: jathan;  state: Exp;  lines: +1 -0
    This is my commit message
    ----------------------------
    revision 1.1
    date: 2011/07/08 20:56:53;  author: jathan;  state: Exp;
    first commit
    """
    def __init__(self, filename, create=True):
        self.locked = False
        self.filename = filename

        if not os.path.exists(filename):
            if not create:
                self.filename = None
                return None
            try:
                f = open(self.filename, 'w')
            except:
                return None
            f.close()
            if not self.checkin(initial=True):
                return None

    def checkin(self, logmsg='none', initial=False, verbose=False):
        """
        Perform an RCS checkin. If successful this also unlocks the file, so
        there is no need to unlock it afterward.

        :param logmsg: The RCS commit message
        :param initial: Initialize a new RCS file, but do not deposit any revision
        :param verbose: Print command output

        >>> rcs.checkin('This is my commit message')
        True
        """
        if initial:
            cmd = 'ci -m"first commit" -t- -i %s' % self.filename
        else:
            cmd = 'ci -u -m"%s" %s' % (logmsg, self.filename)
        status, output = commands.getstatusoutput(cmd)

        if verbose:
            print output

        if status > 0:
            return False

        return True

    def lock(self, verbose=False):
        """
        Perform an RCS checkout with lock. Returns boolean of whether lock
        was sucessful.

        :param verbose: Print command output

        >>> rcs.lock()
        True
        """
        cmd = 'co -f -l %s' % self.filename
        status, output = commands.getstatusoutput(cmd)

        if verbose:
            print output

        if status > 0:
            return False
        
        self.locked = True
        return True

    def unlock(self, verbose=False):
        """
        Perform an RCS checkout with unlock (for cancelling changes).

        :param verbose: Print command output

        >>> rcs.unlock()
        True
        """
        cmd = 'co -f -u %s' % self.filename
        status, output = commands.getstatusoutput(cmd)

        if verbose:
            print output

        if status > 0:
            return False
        
        self.locked = False
        return True

    def lock_loop(self, callback=None, timeout=5, verbose=False):
        """
        Keep trying to lock the file until a lock is obtained.

        :param callback: The function to call after lock is complete
        :param timeout: How long to sleep between lock attempts
        :param verbose: Print command output

        Default:
            >>> rcs.lock_loop(timeout=1) 
            Sleeping to wait for the lock on the file: foo
            Sleeping to wait for the lock on the file: foo

        Verbose:
            >>> rcs.lock_loop(timeout=1, verbose=True)
            RCS/foo,v  -->  foo
            co: RCS/foo,v: Revision 1.2 is already locked by joe.
            Sleeping to wait for the lock on the file: foo
            RCS/foo,v  -->  foo
            co: RCS/foo,v: Revision 1.2 is already locked by joe.
        """
        while not self.lock(verbose=verbose):
            print 'Sleeping to wait for the lock on the file: %s' % self.filename
            time.sleep(timeout)
            if callback:
                callback()
        return True

    def log(self):
        """Returns the RCS log as a string (see above)."""
        cmd = 'rlog %s 2>&1' % self.filename
        status, output = commands.getstatusoutput(cmd)

        if status > 0:
            return None

        return output
