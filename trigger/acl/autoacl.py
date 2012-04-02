#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module controls when ACLs get auto-applied to network devices,
in addition to what is specified in acls.db. 

This is primarily used by :class:`~trigger.acl.db.AclsDB` to populate the
**implicit** ACL-to-device mappings.

No changes should be made to this module. You must specify the path to the
autoacl logic inside of ``settings.py`` as ``AUTOACL_FILE``. This will be
exported as ``autoacl`` so that the module path for the :func:`autoacl()`
function will still be :func:`trigger.autoacl.autoacl`.

This trickery allows us to keep the business-logic for how ACLs are mapped to
devices out of the Trigger packaging.
"""

__author__ = 'Jathan McCollum, Eileen Tschetter'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2010-2011, AOL Inc.'

from trigger.conf import settings, import_path

__all__ = ('autoacl',)

module_path = settings.AUTOACL_FILE

# Placeholder for the custom autoacl module that will provide the autoacl() function
_autoacl_module = import_path(module_path, '_autoacl_module')

# And then this is all we're exporting. Kind of cool, eh?
try:
    from _autoacl_module import autoacl
except ImportError:
    msg = 'Function autoacl() could not be found in %s, please fix!' % module_path
    print msg
    raise
