.. Trigger documentation master file, created by
   sphinx-quickstart on Wed Jul  6 15:17:22 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

To illustrate how Trigger works, here are some basic examples of leveraging the
API.

For these examples to work you must have already :ref:`installed
<install-docs>` and :ref:`configured <config-docs>` Trigger, so if you haven't
already please do that first!

Simple Examples
---------------

Working with metadata
~~~~~~~~~~~~~~~~~~~~~

Get a count of all your devices::

    >>> from trigger.netdevices import NetDevices
    >>> nd = NetDevices()
    >>> len(nd)
    5539

(Whoa! That's a lot!) Let's look up a device.

::

    >>> dev = nd.find('edge1-abc')
    >>> dev.vendor, dev.deviceType
    (<Vendor: Juniper>, 'ROUTER')
    >>> dev.has_ssh()
    True

Get an interactive shell
~~~~~~~~~~~~~~~~~~~~~~~~

Since this device has SSH, let's connect to it!

::

    >>> dev = nd.find('edge1-abc')
    >>> dev.connect()
    Connecting to edge1-abc.net.aol.com.  Use ^X to exit.

    Fetching credentials from /home/jathan/.tacacsrc
    --- JUNOS 10.2S6.3 built 2011-01-22 20:06:27 UTC
    jathan@edge1-abc>

Work with access-lists
~~~~~~~~~~~~~~~~~~~~~~

Let's start with a simple Cisco ACL::

    >>> from trigger.acl import parse
    >>> aclobj = parse("""access-list 123 permit tcp any host 10.20.30.40 eq 80""")
    >>> aclobj.terms
    [<Term: None>]

And convert it to Juniper format::

    >>> aclobj.name_terms() # Juniper policy terms must have names
    >>> aclobj.terms
    [<Term: T1>]
    >>> print '\n'.join(aclobj.output(format='junos'))
    filter 123 {
        term T1 {
            from {
                destination-address {
                    10.20.30.40/32;
                }
                protocol tcp;
                destination-port 80;
            }
            then {
                accept;
            }
        }
    }

Cache your login credentials
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Trigger will encrypt and store your credentials in a file called ``.tacacsrc``
in your home directory. We already had them cached in the previous examples, so
I removed it and then::

    >>> from trigger.tacacsrc import Tacacsrc
    >>> tcrc = Tacacsrc()
    /home/jathan/.tacacsrc not found, generating a new one!

    Updating credentials for device/realm 'tacacsrc'
    Username: jathan
    Password: 
    Password (again): 
    >>> tcrc.creds['aol']
    Credentials(username='jathan', password='boguspassword', realm='tacacsrc')

Passwords can be cached by realm. By default this realm is ``'aol'``, but you
can change that in the settings. Your credentials are encrypted and decrypted
using a shared key. A more secure experimental GPG-encrypted method is in the
works.

Login to a device using the ``gong`` script
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Trigger includes a simple tool for end-users to connect to devices called
``gong``. (It should be just ``go`` but we're in the future, so...)::

    $ gong foo1-cisco
    Connecting to foo1-cisco.net.aol.com.  Use ^X to exit.

    Fetching credentials from /home/jathan/.tacacsrc
    foo1-cisco#
    foo1-abc#show clock
    20:52:05.777 UTC Sat Jun 23 2012
    foo1-cisco#

Partial hostnames are supported, too::

    $ gong foo1
    2 possible matches found for 'foo1':
    [ 1] foo1-abc.net.aol.com
    [ 2] foo1-xyz.net.aol.com
    [ 0] Exit

    Enter a device number: 2
    Connecting to foo1-xyz.net.aol.com.  Use ^X to exit.

    Fetching credentials from /home/jathan/.tacacsrc
    foo1-xyz#

Slightly Advanced Examples
--------------------------

Execute commands asynchronously using Twisted
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a little more advanced... so we saved it for last.

Trigger uses Twisted, which is a callback-based event loop. Wherever possible Twisted's implementation details are abstracted away, but the power is there for those who choose to wield it. Here's a super simplified example of how this might be accomplished::

    from trigger.netdevices import NetDevices
    from twisted.internet import reactor

    nd = NetDevices()
    dev = nd.find('foo1-abc')

    def print_result(data):
        """Display results from a command"""
        print 'Result:', data

    def stop_reactor(data):
        """Stop the event loop"""
        print 'Stopping reactor'
        if reactor.running:
            reactor.stop()

    # Create an event chain that will execute a given list of commands on this
    # device
    async = dev.execute(['show clock'])

    # When we get results from the commands executed, call this
    async.addCallback(print_result)

    # Once we're out of commands, or we an encounter an error, call this
    async.addBoth(stop_reactor)     

    # Start the event loop
    reactor.run()

Which outputs::

    Result: ['21:27:46.435 UTC Sat Jun 23 2012\n']
    Stopping reactor

Execute commands asynchronously using the Commando API
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`~trigger.cmds.Commando` tries to hide Twisted's implementation details so you don't have to deal with callbacks. It is a base class that is intended to be extended to perform the operations you desire. Here is a basic example of how we might perform the same example above using ``Commando`` instead::

    from trigger.cmds import Commando

    class ShowClock(Commando):
        """Execute 'show clock' on a list of Cisco devices."""
        vendors = ['cisco']
        commands = ['show clock']

        def to_cisco(self, device, commands=None, extra=None):
            """Passes the commands as-is to the device"""
            print "Sending %r to %s" % (self.commands, device)
            return self.commands

        def from_cisco(self, results, device):
            """Capture the command output and move on"""
            if device.nodeName not in self.results:
                self.results[device.nodeName] = {}
    
            # Store each command and its result for this device
            for cmd, result in zip(self.commands, results):
                self.results[device.nodeName][cmd] = result

    if __name__ == '__main__':
        device_list = ['foo1-abc.net.aol.com', 'foo2-xyz.net.aol.com']
        showclock = ShowClock(devices=device_list)
        showclock.run() # Commando exposes this to start the event loop

        print '\nResults:'
        print showclock.results

Which outputs::

    Sending ['show clock'] to foo2-xyz.net.aol.com
    Sending ['show clock'] to foo1-abc.net.aol.com

    Results:
    {
        'foo1-abc.net.aol.com': {
            'show clock': '21:56:44.704 UTC Sat Jun 23 2012\n'
        },
        'foo2-xyz.net.aol.com': {
            'show clock': '21:56:44.701 UTC Sat Jun 23 2012\n'
        }
    }
