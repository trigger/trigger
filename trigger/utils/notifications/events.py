# -*- coding: utf-8 -*-

"""
Event objects for the notification system.

These are intended to be used within event handlers such as
`~trigger.utils.notifications.handlers.email_handler()`.

If not customized within :setting:`NOTIFICATION_HANDLERS`, the default
notification type is an `~trigger.utils.notification.events.EmailEvent` that is
handled by `~trigger.utils.notifications.handlers.email_handler`.
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2012-2012, AOL Inc.'

import socket
from trigger.conf import settings


# Exports
__all__ = ('Event', 'Notification', 'EmailEvent')


# Classes
class Event(object):
    """
    Base class for events.
   
    It just populates the attribute dict with all keyword arguments thrown at
    the constructor.

    All ``Event`` objects are expected to have a ``.handle()`` method that
    willl be called by a handler function. Any user-defined event objects must
    have a working ``.handle()`` method that returns ``True`` upon success or
    ``None`` upon a failure when handling the event passed to it.

    If you specify ``required_args``, these must have a value other than
    ``None`` when passed to the constructor.
    """
    required_args = ()

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs) # Brute force wins!
        local_vars = self.__dict__
        for var, value in local_vars.iteritems():
            if var in self.required_args and value is None:
                raise SyntaxError('`%s` is a required argument' % var)

    def __repr__(self):
        return '<%s>' % self.__class__.__name__

    def handle(self):
        raise NotImplementedError('Define me in your subclass!')

class Notification(Event):
    """
    Base class for notification events.

    The ``title`` and ``message`` arguments are the only two that are required.
    This is to simplify the interface when sending notifications and will cause
    notifications to send from the default ``sender to the default
    ``recipients`` that are specified withing the global settings.

    If ``sender`` or ``recipients`` are specified, they will override the
    global defaults.

    Note that this base class has no ``.handle()`` method defined.

    :param title:
        The title/subject of the notification
  
    :param message:
        The message/body of the notification

    :param sender:
        A string representing the sender of the notification (such as an email
        address or a hostname)
  
    :param recipients:
        An iterable containing strings representing the recipients of of the
        notification (such as a list of emails or hostnames)
  
    :param event_status:
        Whether this event is a `failure` or a `success`
    """
    required_args = ('title', 'message')
    status_map = {
            'success': settings.SUCCESS_RECIPIENTS,
            'failure': settings.FAILURE_RECIPIENTS,
    }
    default_sender = settings.NOTIFICATION_SENDER

    def __init__(self, title=None, message=None, sender=None, recipients=None,
                 event_status='failure', **kwargs):
        self.title = title
        self.message = message

        # If the sender isn't specified, use the global sender
        if sender is None:
            sender = self.default_sender
        self.sender = sender

        # We want to know whether we're sending a failure or success email
        if event_status not in self.status_map:
            raise SyntaxError('`event_status` must be in `status_map`')
        self.event_status = event_status

        # If recipients aren't specified, use the global success/failure
        # recipients
        if recipients is None:
            recipients = self.status_map.get(self.event_status)
        self.recipients = recipients

        super(Notification, self).__init__(**kwargs)
        self.kwargs = kwargs

class EmailEvent(Notification):
    """
    An email notification event.
    """
    default_sender = settings.EMAIL_SENDER
    status_map = {
            'success': settings.SUCCESS_EMAILS,
            'failure': settings.FAILURE_EMAILS,
    }
    mailhost = 'localhost'

    def handle(self):
        from trigger.utils.notifications import send_email
        try:
            # This should return True upon successfully sending email
            e = self
            return send_email(addresses=e.recipients, subject=e.title,
                              body=e.message, sender=e.sender,
                              mailhost=e.mailhost)
        except Exception as err:
            print 'Got exception', err
            return None
