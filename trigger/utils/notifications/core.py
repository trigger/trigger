# -*- coding: utf-8 -*-

"""
Basic functions for sending notifications.
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2012-2012, AOL Inc.'

from . import handlers


# Exports
__all__ = ('send_email', 'send_notification')


# Functions
def send_email(addresses, subject, body, sender, mailhost='localhost', mailuser='', mailpass='', ssl=False):
    """
    Sends an email to a list of recipients. Returns ``True`` when done.

    :param addresses:
        List of email recipients

    :param subject:
        The email subject

    :param body:
        The email body

    :param sender:
        The email sender

    :param mailhost:
        (Optional) Mail server address
    """
    import smtplib
    for email in addresses:
        header = 'From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n' % \
            (sender, email, subject )
        message = header + body
        if ssl:
            server = smtplib.SMTP_SSL(mailhost, port=smtplib.SMTP_SSL_PORT)
            server.login(mailuser, mailpass)
            server.sendmail(sender, email, message)
            server.quit()
        else:
            server = smtplib.SMTP(mailhost)
            server.sendmail(sender, email, message)
            server.quit()

    return True

def send_notification(*args, **kwargs):
    """
    Simple entry point into `~trigger.utils.notifications.handlers.notify` that
    takes any arguments and tries to handle them to send a notification.

    This relies on handlers to be definied within
    ``settings.NOTIFICATION_HANDLERS``.
    """
    return handlers.notify(*args, **kwargs)
