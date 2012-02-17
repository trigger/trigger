====================
Managing Credentials
====================

:mod:`trigger.tacacsrc`

About
=====

An abstract interface to .tacacsrc credentials file historically used by NEO developers for caching individual credentials. Supports GPG, which is the preferred method of credential storage, but backwards-compatible with DeviceV2.
Designed to interoperate with the legacy DeviceV2 implementation, but provide a reasonable API on top of that. The name and format of the .tacacsrc file are not ideal, but compatibility matters.

How it works
============

Detail tacacsrc process, integration

Usage
=====

Migrate all documentation from here: http://wiki.office.aol.com/wiki/Trigger/Ops4#GPG_authentication_testing