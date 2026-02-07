"""Basic functions for sending notifications."""

__author__ = "Jathan McCollum"
__maintainer__ = "Jathan McCollum"
__email__ = "jathan.mccollum@teamaol.com"
__copyright__ = "Copyright 2012-2012, AOL Inc."

from . import handlers

# Exports
__all__ = ("send_email", "send_notification")


# Functions
def send_email(  # noqa: PLR0913
    addresses,
    subject,
    body,
    sender,
    mailhost="localhost",
    mailuser="",
    mailpass="",
    ssl=False,
):
    """Sends an email to a list of recipients. Returns ``True`` when done.

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

    :param mailuser:
        (Optional) Username for SMTP authentication

    :param mailpass:
        (Optional) Password for SMTP authentication

    :param ssl:
        (Optional) Use SMTP_SSL for secure communication
    """  # noqa: D401
    import smtplib

    for email in addresses:
        header = f"From: {sender}\r\nTo: {email}\r\nSubject: {subject}\r\n\r\n"
        message = header + body
        if ssl:
            server = smtplib.SMTP_SSL(mailhost, port=smtplib.SMTP_SSL_PORT)
            server.login(mailuser, mailpass)
        else:
            server = smtplib.SMTP(mailhost)
        server.sendmail(sender, email, message)
        server.quit()

    return True


def send_notification(*args, **kwargs):
    """Simple entry point into `~trigger.utils.notifications.handlers.notify` that
    takes any arguments and tries to handle them to send a notification.

    This relies on handlers to be definied within
    ``settings.NOTIFICATION_HANDLERS``.
    """  # noqa: D401, D205
    return handlers.notify(*args, **kwargs)
