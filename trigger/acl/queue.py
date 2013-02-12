#coding=utf-8

"""
Database interface for automated ACL queue. Used primarily by ``load_acl`` and
``acl``` commands for manipulating the work queue. 

    >>> from trigger.acl.queue import Queue
    >>> q = Queue()
    >>> q.list()
    (('dc1-abc.net.aol.com', 'datacenter-protect'), ('dc2-abc.net.aol.com',
    'datacenter-protect'))
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2010-2011, AOL Inc.'

import os
import sys
from trigger.conf import settings
from trigger.netdevices import NetDevices
try:
    import MySQLdb
except ImportError:
    MySQLdb = None

# Exports
__all__ = ('Queue', 'QueueError',)

# Exceptions
class QueueError(Exception): pass

# Classes
class Queue(object):
    """
    Interacts with firewalls database to insert/remove items into the queue. You
    may optionally suppress informational messages by passing ``verbose=False``
    to the constructor.

    :param verbose: Toggle verbosity
    :type verbose: Boolean
    """
    def __init__(self, verbose=True):
        self.dbconn = self._get_firewall_db_conn()
        self.cursor = self.dbconn.cursor()
        self.nd = NetDevices()
        self.verbose = verbose

    def _get_firewall_db_conn(self):
        """Returns a MySQL db connection used for the ACL queues using database
        settings found withing ``settings.py``."""
        if MySQLdb is None:
            raise RuntimeError("You must install ``MySQL-python`` to use the queue")
        try:
            return MySQLdb.connect(host=settings.DATABASE_HOST,
                                   db=settings.DATABASE_NAME,
                                   port=settings.DATABASE_PORT,
                                   user=settings.DATABASE_USER,
                                   passwd=settings.DATABASE_PASSWORD)
        # catch if we can't connect, and shut down
        except MySQLdb.OperationalError as e:
            sys.exit("Can't connect to the database - %s (error %d)" % (e[1],e[0]))

    def _normalize(self, arg):
        if arg.startswith('acl.'):
            arg = arg[4:]
        escalation = False
        if arg.upper().endswith(' ESCALATION'):
            escalation = True
            arg = arg[:-11]
        return (escalation, arg)

    def insert(self, acl, routers, escalation=False):
        """
        Insert an ACL and associated devices into the ACL load queue.  

        Attempts to insert into integrated queue.  If ACL test fails, then 
        item is inserted into manual queue.
        """
        assert acl, 'no ACL defined'
        if not routers: 
            routers = []

        (escalation, acl) = self._normalize(acl)
        if len(routers):
            for router in routers:
                try:
                    dev = self.nd.find(router)
                except KeyError:
                    raise  "Could not find %s in netdevices" % router
                    return
                if acl not in dev.acls:
                    raise "Could not find %s in %s's acl list" % (acl, router)
                    return

                self.cursor.execute('''insert into acl_queue 
                                        (acl, router, queued, escalation) 
                                        values (%s, %s, now(), %s)''', 
                                        (acl, router, escalation))

            if self.verbose:
                print 'ACL', acl, 'injected into integrated load queue for',
                print ', '.join([dev[:dev.find('.')] for dev in routers])

        else:
            self.cursor.execute('''insert into queue (q_name, login) values (%s, %s)''',
                                    (acl, os.getlogin()))
            if self.verbose: print '"%s" injected into manual load queue' % acl

        self.dbconn.commit()

    def delete(self, acl, routers=None, escalation=False):
        """
        Delete an ACL from the firewall database queue.

        Attempts to delete from integrated queue.  If ACL test fails, then 
        item is deleted from manual queue.
        """
        assert acl, 'no ACL defined' 
        (escalation, acl) = self._normalize(acl)

        if routers is not None:
            devs = routers
        else:
            if self.verbose: print 'fetching routers from database'
            self.cursor.execute('''select distinct router from acl_queue
                                where acl = %s and loaded is null
                                order by router''', (acl,))
            rows = self.cursor.fetchall()
            devs = [row[0] for row in rows] or []

        if len(devs):
            for dev in devs:
                self.cursor.execute('''delete from acl_queue where acl=%s and 
                                    router=%s and loaded is null''', (acl, dev))

            if self.verbose:
                print 'ACL', acl, 'cleared from integrated load queue for',
                print ', '.join([dev[:dev.find('.')] for dev in devs])
        elif self.cursor.execute('''delete from queue
                                where q_name = %s and done = 0''', (acl,)):
            if self.verbose: print '"%s" cleared from manual load queue' % acl
        else:
            if self.verbose: print '"%s" not found in manual or integrated queues' % acl

        self.dbconn.commit()

    def complete(self, device, acls):
        """
        Integrated queue only.

        Mark a device and associated ACLs as complete my updating loaded to
        current timestampe.  Migrated from clear_load_queue() in load_acl.
        """
        for acl in acls:
            self.cursor.execute("""update acl_queue set loaded=now() where
                                acl=%s and router=%s and loaded is null""",
                                (acl, device))
        if self.verbose: 
            print 'Marked the following ACLs as complete for %s: ' % device
            print ', '.join(acls)

    def remove(self, acl, routers, escalation=False):
        """
        Integrated queue only.

        Mark an ACL and associated devices as "removed" (loaded=0). Intended
        for use when performing manual actions on the load queue when
        troubleshooting or addressing errors with automated loads.  This leaves
        the items in the database but removes them from the active queue.
        """
        assert acl, 'no ACL defined' 
        for router in routers:
            self.cursor.execute("""update acl_queue set loaded=0 where acl=%s
                                and router=%s and loaded is null""", (acl, router))
        if self.verbose: 
            print 'Marked the following devices as removed for ACL %s: ' % acl
            print ', '.join(routers)

    def list(self, queue='integrated', escalation=False):
        """
        List items in the queue, defauls to integrated queue.

        Valid queue arguments are 'integrated' or 'manual'.
        """
        if queue == 'integrated':
            query = 'select distinct router, acl from acl_queue where loaded is null'
            if escalation:
                query += ' and escalation = true' 
        elif queue == 'manual':
            query = 'select q_name, login, q_ts, done from queue where done=0'
        else:
            print 'Queue must be integrated or manual, you specified: %s' % queue
            return False

        self.cursor.execute(query)
        all_data = self.cursor.fetchall()

        self.dbconn.commit()

        return all_data
