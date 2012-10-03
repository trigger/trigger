# -*- coding: utf-8 -*-

"""
Utils to import modules.

Taken verbatim from ``django.utils.importlib`` in Django 1.4.
"""

import os
import sys


# Exports
__all__ = ('import_module', 'import_module_from_path')


# Functions
def _resolve_name(name, package, level):
    """Return the absolute name of the module to be imported."""
    if not hasattr(package, 'rindex'):
        raise ValueError("'package' not set to a string")
    dot = len(package)
    for x in xrange(level, 1, -1):
        try:
            dot = package.rindex('.', 0, dot)
        except ValueError:
            raise ValueError("attempted relative import beyond top-level "
                              "package")
    return "%s.%s" % (package[:dot], name)

def import_module(name, package=None):
    """
    Import a module and return the module object.

    The ``package`` argument is required when performing a relative import. It
    specifies the package to use as the anchor point from which to resolve the
    relative import to an absolute import.

    """
    if name.startswith('.'):
        if not package:
            raise TypeError("relative imports require the 'package' argument")
        level = 0
        for character in name:
            if character != '.':
                break
            level += 1
        name = _resolve_name(name[level:], package, level)
    __import__(name)
    return sys.modules[name]

def import_module_from_path(full_path, global_name):
    """
    Import a module from a file path and return the module object.

    Allows one to import from anywhere, something ``__import__()`` does not do.
    The module is added to ``sys.modules`` as ``global_name``.

    :param full_path:
        The absolute path to the module .py file

    :param global_name:
        The name assigned to the module in sys.modules. To avoid
        confusion, the global_name should be the same as the variable to which
        you're assigning the returned module.
    """
    path, filename = os.path.split(full_path)
    module, ext = os.path.splitext(filename)
    sys.path.append(path)

    try:
        mymodule = __import__(module)
        sys.modules[global_name] = mymodule
    except ImportError:
        raise ImportError('Module could not be imported from %s.' % full_path)
    finally:
        del sys.path[-1]

    return mymodule
