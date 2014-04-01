# -*- coding: utf-8 -*-

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
__email__ = 'jmccollum@salesforce.com'
__version__ = '2.0.1'


import datetime
import os
import sys
from trigger import exceptions
from trigger.conf import settings
from trigger.netdevices import NetDevices
from trigger.utils import get_user
from . import models


# Globals
QUEUE_NAMES = ('integrated', 'manual')


# Exports
__all__ = ('Queue',)


# Classes
class Queue(object):
    """
    Interacts with firewalls database to insert/remove items into the queue.

    :param verbose:
        Toggle verbosity

    :type verbose:
        Boolean
    """
    def __init__(self, verbose=True):
        self.nd = NetDevices()
        self.verbose = verbose
        self.login = get_user()

    def vprint(self, msg):
        """
        Print something if ``verbose`` instance variable is set.

        :param msg:
            The string to print
        """
        if self.verbose:
            print msg

    def get_model(self, queue):
        """
        Given a queue name, return its DB model.

        :param queue:
            Name of the queue whose object you want
        """
        return models.MODEL_MAP.get(queue, None)

    def create_task(self, queue, *args, **kwargs):
        """
        Create a task in the specified queue.

        :param queue:
            Name of the queue whose object you want
        """
        model = self.get_model(queue)
        taskobj = model.create(*args, **kwargs)

    def _normalize(self, arg, prefix=''):
        """
        Remove ``prefix`` from ``arg``, and set "escalation" bit.

        :param arg:
            Arg (typically an ACL filename) to trim

        :param prefix:
            Prefix to trim from arg
        """
        if arg.startswith(prefix):
            arg = arg[len(prefix):]
        escalation = False
        if arg.upper().endswith(' ESCALATION'):
            escalation = True
            arg = arg[:-11]
        return (escalation, arg)

    def insert(self, acl, routers, escalation=False):
        """
        Insert an ACL and associated devices into the ACL load queue.

        Attempts to insert into integrated queue. If ACL test fails, then
        item is inserted into manual queue.

        :param acl:
            ACL name

        :param routers:
            List of device names

        :param escalation:
            Whether this is an escalated task
        """
        if not acl:
            raise exceptions.ACLQueueError('You must specify an ACL to insert into the queue')
        if not routers:
            routers = []

        escalation, acl = self._normalize(acl)
        if routers:
            for router in routers:
                try:
                    dev = self.nd.find(router)
                except KeyError:
                    msg = 'Could not find device %s' % router
                    raise exceptions.TriggerError(msg)

                if acl not in dev.acls:
                    msg = "Could not find %s in ACL list for %s" % (acl, router)
                    raise exceptions.TriggerError(msg)

                self.create_task(queue='integrated', acl=acl, router=router,
                                 escalation=escalation)

            self.vprint('ACL %s injected into integrated load queue for %s' %
                        (acl, ', '.join(dev[:dev.find('.')] for dev in routers)))

        else:
            self.create_task(queue='manual', q_name=acl, login=self.login)
            self.vprint('"%s" injected into manual load queue' % acl)

    def delete(self, acl, routers=None, escalation=False):
        """
        Delete an ACL from the firewall database queue.

        Attempts to delete from integrated queue. If ACL test fails
        or if routers are not specified, the item is deleted from manual queue.

        :param acl:
            ACL name

        :param routers:
            List of device names. If this is ommitted, the manual queue is used.

        :param escalation:
            Whether this is an escalated task
        """
        if not acl:
            raise exceptions.ACLQueueError('You must specify an ACL to delete from the queue')

        escalation, acl = self._normalize(acl)
        m = self.get_model('integrated')

        if routers is not None:
            devs = routers
        else:
            self.vprint('Fetching routers from database')
            result = m.select(m.router).distinct().where(
                              m.acl == acl, m.loaded >> None).order_by(m.router)
            rows = result.tuples()
            devs = [row[0] for row in rows]

        if devs:
            for dev in devs:
                m.delete().where(m.acl == acl, m.router == dev,
                                 m.loaded >> None).execute()

            self.vprint('ACL %s cleared from integrated load queue for %s' %
                        (acl, ', '.join(dev[:dev.find('.')] for dev in devs)))
            return True

        else:
            m = self.get_model('manual')
            if m.delete().where(m.q_name == acl, m.done == False).execute():
                self.vprint('%r cleared from manual load queue' % acl)
                return True

        self.vprint('%r not found in any queues' % acl)
        return False

    def complete(self, device, acls):
        """
        Mark a device and its ACLs as complete using current timestamp.

        (Integrated queue only.)

        :param device:
            Device names

        :param acls:
            List of ACL names
        """
        m = self.get_model('integrated')
        for acl in acls:
            now = loaded=datetime.datetime.now()
            m.update(loaded=now).where(m.acl == acl, m.router == device,
                                       m.loaded >> None).execute()

        self.vprint('Marked the following ACLs as complete for %s:' % device)
        self.vprint(', '.join(acls))

    def remove(self, acl, routers, escalation=False):
        """
        Integrated queue only.

        Mark an ACL and associated devices as "removed" (loaded=0). Intended
        for use when performing manual actions on the load queue when
        troubleshooting or addressing errors with automated loads. This leaves
        the items in the database but removes them from the active queue.

        :param acl:
            ACL name

        :param routers:
            List of device names

        :param escalation:
            Whether this is an escalated task
        """
        if not acl:
            raise exceptions.ACLQueueError('You must specify an ACL to remove from the queue')

        m = self.get_model('integrated')
        loaded = 0
        if settings.DATABASE_ENGINE == 'postgresql':
            loaded = '-infinity' # See: http://bit.ly/15f0J3z
        for router in routers:
            m.update(loaded=loaded).where(m.acl == acl, m.router == router,
                                          m.loaded >> None).execute()

        self.vprint('Marked the following devices as removed for ACL %s: ' % acl)
        self.vprint(', '.join(routers))

    def list(self, queue='integrated', escalation=False, q_names=QUEUE_NAMES):
        """
        List items in the specified queue, defauls to integrated queue.

        :param queue:
            Name of the queue to list

        :param escalation:
            Whether this is an escalated task

        :param q_names:
            (Optional) List of valid queue names
        """
        if queue not in q_names:
            self.vprint('Queue must be one of %s, not: %s' % (q_names, queue))
            return False

        m = self.get_model(queue)

        if queue == 'integrated':
            result = m.select(m.router, m.acl).distinct().where(
                              m.loaded >> None, m.escalation == escalation)
        elif queue == 'manual':
            result = m.select(m.q_name, m.login, m.q_ts, m.done).where(
                              m.done == False)
        else:
            raise RuntimeError('This should never happen!!')

        all_data = list(result.tuples())
        return all_data
