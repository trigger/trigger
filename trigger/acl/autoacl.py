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

If you do not specify a location for ``AUTOACL_FILE`` or the module cannot be
loaded, then a default :func:`autoacl()` function ill be used.
"""

__author__ = 'Jathan McCollum, Eileen Tschetter'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2010-2012, AOL Inc.'

import warnings
from trigger.conf import settings, import_path

__all__ = ('autoacl',)

module_path = settings.AUTOACL_FILE


# In either case we're exporting a single name: autoacl().
try:
    # Placeholder for the custom autoacl module that will provide the autoacl()
    # function. Either of these operations will raise an ImportError if they
    # don't work, so it's safe to have them within the same try statement.
    _autoacl_module = import_path(module_path, '_autoacl_module')
    from _autoacl_module import autoacl
except ImportError:
    msg = 'Function autoacl() could not be found in %s, using default!' % module_path
    warnings.warn(msg, RuntimeWarning)
    def autoacl(dev, explicit_acls=None):
        """
        Default fallback autoacl function with the same argument signature
        as as is expected, but Does nothing with the arguments. Returns an empty set.
        """
        return set()
