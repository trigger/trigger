"""
Trigger Twisted XMLRPC server with an SSH manhole. Supports SSL.

This provides a daemonized Twisted reactor loop, Trigger and client
applications do not have to co-habitate. Using the XMLRPC server model, all
Trigger compatibility tasks can be executed using simple XMLRPC clients that
call the appropriate method with arguments on the local XMLRPC server instance.

New methods can be added by way of plugins.

See ``examples/xmlrpc_server`` in the Trigger source distribution for a simple
usage example.
"""

import os
import sys
import types

from trigger.contrib.commando import CommandoApplication
from trigger.utils import importlib
from twisted.internet import defer
from twisted.python import log
from twisted.web import xmlrpc, server


# Enable Deferred debuging if ``DEBUG`` is set.
if os.getenv('DEBUG'):
    defer.setDebugging(True)


class TriggerXMLRPCServer(xmlrpc.XMLRPC):
    """
    Twisted XMLRPC server front-end for Commando
    """
    def __init__(self, *args, **kwargs):
        xmlrpc.XMLRPC.__init__(self, *args, **kwargs)
        self.allowNone = True
        self.useDateTime = True

        self._handlers = []
        self._procedure_map = {}
        self.addHandlers(self._handlers)

    def lookupProcedure(self, procedurePath):
        """
        Lookup a method dynamically.

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
                raise xmlrpc.NoSuchFunction(self.NOT_FOUND,
                                            "no such subHandler %s" % prefix)
            return handler.lookupProcedure(procedurePath)

        # Try self-defined methods first...
        f = getattr(self, "xmlrpc_%s" % procedurePath, None)

        # Try mapped methods second...
        if f is None:
            f = self._procedure_map.get(procedurePath, None)

        if not f:
            raise xmlrpc.NoSuchFunction(self.NOT_FOUND,
                "procedure %s not found" % procedurePath)
        elif not callable(f):
            raise xmlrpc.NoSuchFunction(self.NOT_FOUND,
                "procedure %s not callable" % procedurePath)
        else:
            return f

    def addHandlers(self, handlers):
        """Add multiple handlers"""
        for handler in handlers:
            self.addHandler(handler)

    def addHandler(self, handler):
        """
        Add a handler and bind it to an XMLRPC procedure.

        Handler must a be a function or an instance of an object with handler
        methods.
        """
        # Register it
        log.msg("Adding handler: %s" % handler)
        self._handlers.append(handler)

        # If it's a function, bind it as its own internal name.
        if type(handler) in (types.BuiltinFunctionType, types.FunctionType):
            name = handler.__name__
            if name.startswith('xmlrpc_'):
                name = name[7:] # If it starts w/ 'xmlrpc_', slice it out!
            log.msg("Mapping function %s..." % name)
            self._procedure_map[name] = handler
            return None

        # Otherwise, walk the methods on any class objects and bind them by
        # their attribute name.
        for method in dir(handler):
            if not method.startswith('_'):
                log.msg("Mapping method %s..." % method)
                self._procedure_map[method] = getattr(handler, method)

    def listProcedures(self):
        """Return a list of the registered procedures"""
        return self._procedure_map.keys()

    def xmlrpc_add_handler(self, mod_name, task_name, force=False):
        """
        Add a handler object from a remote call.
        """
        module = None
        if mod_name in sys.modules:
            # Check if module is already loaded
            if force:
                log.msg("Forcing reload of handler: %r" % task_name)
                # Allow user to force reload of module
                module = reload(sys.modules[mod_name])
            else:
                # If not forcing reload, don't bother with the rest
                log.msg("%r already loaded" % mod_name)
                return None
        else:
            log.msg("Trying to add handler: %r" % task_name)
            try:
                module = importlib.import_module(mod_name, __name__)
            except NameError as msg:
                log.msg('NameError: %s' % msg)
            except:
                pass

        if not module:
            log.msg("    Unable to load module: %s" % mod_name)
            return None
        else:
            handler = getattr(module, 'xmlrpc_' + task_name)
            # XMLRPC methods will not accept kwargs. Instead, we pass 2 position
            # args: args and kwargs, to a shell method (dummy) that will explode
            # them when sending to the user defined method (handler).
            def dummy(self, args, kwargs):
                return handler(*args, **kwargs)

            # TODO (jathan): Make this work!!
            # This just simply does not work.  I am not sure why, but it results in a
            # "<Fault 8001: 'procedure config_device not found'>" error!
            # # Bind the dummy shell method to TriggerXMLRPCServer. The function's
            # # name will be used to map it to the "dummy" handler object.
            # dummy.__name__ = task_name
            # self.addHandler(dummy)

            # This does work.
            # Bind the dummy shell method to TriggerXMLRPCServer as 'xmlrpc_' + task_name
            setattr(TriggerXMLRPCServer, 'xmlrpc_' + task_name, dummy)

    def xmlrpc_list_subhandlers(self):
        return list(self.subHandlers)

    def xmlrpc_execute_commands(self, args, kwargs):
        """Execute ``commands`` on ``devices``"""
        c = CommandoApplication(*args, **kwargs)
        d = c.run()
        return d

    def xmlrpc_add(self, x, y):
        """Adds x and y"""
        return x + y

    def xmlrpc_fault(self):
        """
        Raise a Fault indicating that the procedure should not be used.
        """
        raise xmlrpc.Fault(123, "The fault procedure is faulty.")

    def _ebRender(self, failure):
        """
        Custom exception rendering.
        Ref: https://netzguerilla.net/iro/dev/_modules/iro/view/xmlrpc.html
        """
        if isinstance(failure.value, Exception):
            msg = """%s: %s""" % (failure.type.__name__, failure.value.args[0])
            return xmlrpc.Fault(400, msg)
        return super(TriggerXMLRPCServer, self)._ebRender(self, failure)

# XXX (jathan): Note that this is out-of-sync w/ the twistd plugin and is
# probably broken.
def main():
    """To daemonize as a twistd plugin! Except this doesn't work and these"""
    from twisted.application.internet import TCPServer, SSLServer
    from twisted.application.service import Application
    from twisted.internet import ssl

    rpc = TriggerXMLRPCServer()
    xmlrpc.addIntrospection(rpc)

    server_factory = server.Site(rpc)
    application = Application('trigger_xmlrpc')

    #xmlrpc_service = TCPServer(8000, server_factory)
    ctx = ssl.DefaultOpenSSLContextFactory('server.key', 'cacert.pem')
    xmlrpc_service = SSLServer(8000, server_factory, ctx)
    xmlrpc_service.setServiceParent(application)

    return application

if __name__ == '__main__':
    # To run me as a daemon:
    # twistd -l server.log --pidfile server.pid -y server.py
    application = main()
