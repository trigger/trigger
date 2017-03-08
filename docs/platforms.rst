Supported Platforms
===================

Trigger currently officially supports devices manufactured by the following
vendors:

+ A10 Networks

  - All AX-series application delivery controllers and server load-balancers

+ Arista Networks

  - All 7000-family switch platforms

+ Aruba Networks

  - All Mobility Controller platforms

+ Avocent (Emerson)

  - All Cyclades ACS 6000-series console terminal servers

+ Brocade Networks

  - ADX application delivery switches
  - MLX routers
  - VDX switches

+ Citrix Systems

  - NetScaler application delivery controllers and server load-balancers

+ Cisco Systems

  - All router and switch platforms running IOS
  - All firewalls running ASA software (NetACLInfo not implemented)
  - All switch platforms running NX-OS

+ Dell

  - PowerConnect switches

+ F5 Networks

  - All BIG-IP application delivery controllers and server load-balancers

+ Force10

  - All router and switch platforms running FTOS

+ Foundry/Brocade

  - All router and switch platforms (NetIron, ServerIron, et al.)

+ Juniper Networks

  - All router, switch, and firewall platforms running Junos
  - NetScreen firewalls running ScreenOS

+ MRV Communications

  - All LX-series console terminal servers

It's worth noting that other vendors may actually work with the current
libraries, but they have not been tested. The mapping of supported platforms is
specified in ``settings.py`` as :setting:`SUPPORTED_PLATFORMS`. Modify it at
your own risk!
