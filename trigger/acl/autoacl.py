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

from trigger.conf import settings
from trigger.utils.importlib import import_module_from_path
from twisted.python import log
import warnings

__all__ = ('autoacl',)

module_path = settings.AUTOACL_FILE


# In either case we're exporting a single name: autoacl().
try:
    # Placeholder for the custom autoacl module that will provide the autoacl()
    # function. Either of these operations will raise an ImportError if they
    # don't work, so it's safe to have them within the same try statement.
    _autoacl_module = import_module_from_path(module_path, '_autoacl_module')
    log.msg('Loading autoacl() from %s' % module_path)
    from _autoacl_module import autoacl
except ImportError:
    msg = 'Function autoacl() could not be found in %s, using default!' % module_path
    warnings.warn(msg, RuntimeWarning)
    def autoacl(dev, explicit_acls=None):
        """
        Given a NetDevice object, returns a set of **implicit** (auto) ACLs. We
        require a device object so that we don't have circular dependencies
        between netdevices and autoacl.

        This function MUST return a ``set()`` of acl names or you will break
        the ACL associations. An empty set is fine, but it must be a set!

        :param dev: A :class:`~trigger.netdevices.NetDevice` object.
        :param explicit_acls: A set containing names of ACLs. Default: set()

        >>> dev = nd.find('test1-abc')
        >>> dev.vendor
        <Vendor: Juniper>
        >>> autoacl(dev)
        set(['juniper-router-protect', 'juniper-router.policer'])

        NOTE: If the default function is returned it does nothing with the
        arguments and always returns an empty set.
        """
        return set()
