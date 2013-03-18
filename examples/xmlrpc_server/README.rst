#############################
Trigger XMLRPC Server Example
#############################

Files
=====

:trigger-xmlrpc.sh:
    Simple startup script that also tails the logfile.

:trigger-xmlrpc.init:
    /etc/init.d script - INCOMPLETE AND PROBABLY BROKEN

:server.key:
    Self-signed server cert private key. For SSL.

:cacert.pem:
    Self-signed CA certificate. For SSL.

:users.txt:
    Passwd (5) user/password file used for auth to the SSH manhole (port 8001)

Dynamically adding new methods
===============================

Consider this example code to bind ``pow()`` to the server::

    import xmlrpclib
    import cPickle as pickle

    s = xmlrpclib.Server('https://localhost:8000/', verbose=True)

    # You have to pickle it because you can't send complex objects over the wire,
    # but since the XMLRPC server is also a Python application, you can have it
    # load and re-create the object.
    s.add_handler(pickle.dumps(pow))

    # Now call the newly added handler... Profit!
    # Should return 243
    print s.pow(3, 5)
