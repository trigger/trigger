"""Trigger Twisted XMLRPC server with an SSH manhole. Supports SSL.

This provides a daemonized Twisted reactor loop, Trigger and client
applications do not have to co-habitate. Using the XMLRPC server model, all
Trigger compatibility tasks can be executed using simple XMLRPC clients that
call the appropriate method with arguments on the local XMLRPC server instance.

New methods can be added by way of plugins.

See ``examples/xmlrpc_server`` in the Trigger source distribution for a simple
usage example.
"""

import importlib
import os
import sys
import types

from twisted.internet import defer
from twisted.python import log
from twisted.web import server, xmlrpc

from trigger.contrib.commando import CommandoApplication
from trigger.utils import importlib as importlib  # noqa: F811

# Enable Deferred debuging if ``DEBUG`` is set.
if os.getenv("DEBUG"):
    defer.setDebugging(True)


class TriggerXMLRPCServer(xmlrpc.XMLRPC):
    """Twisted XMLRPC server front-end for Commando."""

    def __init__(self, *args, **kwargs):
        xmlrpc.XMLRPC.__init__(self, *args, **kwargs)
        self.allowNone = True
        self.useDateTime = True

        self._handlers = []
        self._procedure_map = {}
        self.addHandlers(self._handlers)

    def lookupProcedure(self, procedurePath):
        """Lookup a method dynamically.

        1. First, see if it's provided by a sub-handler.
        2. Or try a self-defined method (prefixed with `xmlrpc_`)
        3. Lastly, try dynamically mapped methods.
        4. Or fail loudly.
        """
        log.msg("LOOKING UP:", procedurePath)

        if procedurePath.find(self.separator) != -1:
            prefix, procedurePath = procedurePath.split(self.separator, 1)
            handler = self.getSubHandler(prefix)
            if handler is None:
                raise xmlrpc.NoSuchFunction(
                    self.NOT_FOUND,
                    f"no such subHandler {prefix}",
                )
            return handler.lookupProcedure(procedurePath)

        # Try self-defined methods first...
        f = getattr(self, f"xmlrpc_{procedurePath}", None)

        # Try mapped methods second...
        if f is None:
            f = self._procedure_map.get(procedurePath, None)

        if not f:
            raise xmlrpc.NoSuchFunction(
                self.NOT_FOUND,
                f"procedure {procedurePath} not found",
            )
        if not callable(f):
            raise xmlrpc.NoSuchFunction(
                self.NOT_FOUND,
                f"procedure {procedurePath} not callable",
            )
        return f

    def addHandlers(self, handlers):
        """Add multiple handlers."""
        for handler in handlers:
            self.addHandler(handler)

    def addHandler(self, handler):
        """Add a handler and bind it to an XMLRPC procedure.

        Handler must a be a function or an instance of an object with handler
        methods.
        """
        # Register it
        log.msg(f"Adding handler: {handler}")
        self._handlers.append(handler)

        # If it's a function, bind it as its own internal name.
        if type(handler) in (types.BuiltinFunctionType, types.FunctionType):
            name = handler.__name__
            name = name.removeprefix(
                "xmlrpc_"
            )  # If it starts w/ 'xmlrpc_', slice it out!
            log.msg(f"Mapping function {name}...")
            self._procedure_map[name] = handler
            return

        # Otherwise, walk the methods on any class objects and bind them by
        # their attribute name.
        for method in dir(handler):
            if not method.startswith("_"):
                log.msg(f"Mapping method {method}...")
                self._procedure_map[method] = getattr(handler, method)

    def listProcedures(self):
        """Return a list of the registered procedures."""
        return self._procedure_map.keys()

    def xmlrpc_add_handler(self, mod_name, task_name, force=False):
        """Add a handler object from a remote call."""
        module = None
        if mod_name in sys.modules:
            # Check if module is already loaded
            if force:
                log.msg(f"Forcing reload of handler: {task_name!r}")
                # Allow user to force reload of module
                module = importlib.reload(sys.modules[mod_name])
            else:
                # If not forcing reload, don't bother with the rest
                log.msg(f"{mod_name!r} already loaded")
                return
        else:
            log.msg(f"Trying to add handler: {task_name!r}")
            try:
                module = importlib.import_module(mod_name, __name__)
            except NameError as msg:
                log.msg(f"NameError: {msg}")
            except:  # noqa: S110
                pass

        if not module:
            log.msg(f"    Unable to load module: {mod_name}")
            return
        handler = getattr(module, "xmlrpc_" + task_name)

        # XMLRPC methods will not accept kwargs. Instead, we pass 2 position
        # args: args and kwargs, to a shell method (dummy) that will explode
        # them when sending to the user defined method (handler).
        def dummy(self, args, kwargs):
            return handler(*args, **kwargs)

        # TODO (jathan): Make this work!!
        # This just simply does not work.  I am not sure why, but it results in a
        # "<Fault 8001: 'procedure config_device not found'>" error!

        # This does work.
        # Bind the dummy shell method to TriggerXMLRPCServer as 'xmlrpc_' + task_name
        setattr(TriggerXMLRPCServer, "xmlrpc_" + task_name, dummy)

    def xmlrpc_list_subhandlers(self):
        return list(self.subHandlers)

    def xmlrpc_execute_commands(self, args, kwargs):
        """Execute ``commands`` on ``devices``."""
        c = CommandoApplication(*args, **kwargs)
        return c.run()

    def xmlrpc_add(self, x, y):
        """Adds x and y."""
        return x + y

    def xmlrpc_fault(self):
        """Raise a Fault indicating that the procedure should not be used."""
        raise xmlrpc.Fault(123, "The fault procedure is faulty.")

    def _ebRender(self, failure):
        """Custom exception rendering.
        Ref: https://netzguerilla.net/iro/dev/_modules/iro/view/xmlrpc.html.
        """
        if isinstance(failure.value, Exception):
            msg = f"""{failure.type.__name__}: {failure.value.args[0]}"""
            return xmlrpc.Fault(400, msg)
        return super()._ebRender(self, failure)


# XXX (jathan): Note that this is out-of-sync w/ the twistd plugin and is
# probably broken.
def main():
    """To daemonize as a twistd plugin! Except this doesn't work and these."""
    from twisted.application.internet import SSLServer
    from twisted.application.service import Application
    from twisted.internet import ssl

    rpc = TriggerXMLRPCServer()
    xmlrpc.addIntrospection(rpc)

    server_factory = server.Site(rpc)
    application = Application("trigger_xmlrpc")

    ctx = ssl.DefaultOpenSSLContextFactory("server.key", "cacert.pem")
    xmlrpc_service = SSLServer(8000, server_factory, ctx)
    xmlrpc_service.setServiceParent(application)

    return application


if __name__ == "__main__":
    # To run me as a daemon:
    # twistd -l server.log --pidfile server.pid -y server.py
    application = main()
