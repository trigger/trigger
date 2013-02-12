# -*- coding: utf-8 -*-

"""
Handlers for event notifications.

Handlers are specified by full module path within
``settings.NOTIFICATION_HANDLERS``. These are then imported and registered
internally in this module.

The primary public interface to this module is
`~trigger.utils.notifications.handlers.notify` which is in turn called by
`~trigger.utils.notifications.send_notification` to send notifications.

Handlers should return ``True`` if they have performed the desired action
or ``None`` if they have not.

A handler can either define its own custom behavior, or leverage a custom
`~trigger.utils.notifications.events.Event` object. The goal was to provide a
simple public interface to customizing event notifications.

If not customized within :setting:`NOTIFICATION_HANDLERS`, the default
notification type is an `~trigger.utils.notification.events.EmailEvent` that is
handled by `~trigger.utils.notifications.handlers.email_handler`.
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2012-2012, AOL Inc.'

from trigger import exceptions
from trigger.utils.importlib import import_module
from . import events

# Globals
# This is where handler functions are stored.
_registered_handlers = []

# And whether they've been successfully registered
HANDLERS_REGISTERED = False


# Exports
__all__ = ('email_handler', 'notify')


# Functions
def email_handler(*args, **kwargs):
    """
    Default email notification handler.
    """
    try:
        event = events.EmailEvent(*args, **kwargs)
    except Exception as err:
        return None
    else:
        return event.handle()

def _register_handlers():
    """
    Walk thru the handlers specified in ``settings.NOTIFICATION_HANDLERS`` and
    register them internally.

    Any built-in event handlers need to be defined above this function.
    """
    global HANDLERS_REGISTERED
    from trigger.conf import settings

    for handler_path in settings.NOTIFICATION_HANDLERS:
        # Get the module and func name
        try:
            h_module, h_funcname = handler_path.rsplit('.', 1)
        except ValueError:
            raise exceptions.ImproperlyConfigured("%s isn't a handler module" % handler_path)

        # Import the module and get the module object
        try:
            mod = import_module(h_module)
        except ImportError as err:
            raise exceptions.ImproperlyConfigured('Error importing handler %s: "%s"' % (h_module, err))

        # Get the handler function
        try:
            handler = getattr(mod, h_funcname)
        except AttributeError:
            raise exceptions.ImproperlyConfigured('Handler module "%s" does not define a "%s" function' % (h_module, h_funcname))

        # Register the handler function
        if handler not in _registered_handlers:
            _registered_handlers.append(handler)

    HANDLERS_REGISTERED = True
_register_handlers() # Do this on init

def notify(*args, **kwargs):
    """
    Iterate thru registered handlers to handle events and send notifications.

    Handlers should return ``True`` if they have performed the desired action
    or ``None`` if they have not.
    """
    if not HANDLERS_REGISTERED:
        _register_handlers()

    for handler in _registered_handlers:
        # Pass the event args to the handler
        #print 'Sending %s, %s to %s' % (args, kwargs, handler)
        try:
            result = handler(*args, **kwargs)
        except Exception as err:
            #print 'Got exception: %s' % err
            continue
        else:
            if result is not None:
                return True # Event was handled!
            else:
                continue
            
    # We don't want to get to this point
    raise RuntimeError('No handlers succeeded for this event: %s' % event)
