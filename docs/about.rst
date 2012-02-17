=============
About Trigger
=============

Trigger is comprised of the following core components:

NetDevices
An abstract interface to network device metadata and security policy associations.

Twister
Asynchronous device interaction library.  Performs login and basic command-line interaction support via telnet or SSH using the Twisted asynchronous I/O framework.

Firewall Policy Parser
Access-list parsing library which contains various modules that allow for parsing, manipulation, and management of network access control lists (ACLs). It will parse a complete ACL and return an ACL object that can be easily translated to any supported vendor syntax.

Change Management
An abstract interface to bounce windows and moratoria. Includes support for RCS version-control system for maintaining configuration data and an integrated automated task queue.

Commands
Command execution library which abstracts the execution of commands on network devices. Allows for integrated parsing and manipulation of return data for rapid integration to existing or newly created tools.

TACACSrc
Network credentials library that provides an abstract interface to storing user credentials encrypted on disk.

