"""
Wrapper for loading metadata from storage of some sort (e.g. filesystem,
database)

This uses NETDEVICE_LOADERS settings, which is a list of loaders to use.
Each loader is expected to have this interface::

    callable(data_source, **kwargs)

``data_source`` is typically a file path from which to load the metadata, but can
be also be a list/tuple of [data_source, *args]
``kwargs`` are any optional keyword arguments you wish to send along.

The loader must return an iterable of key/value pairs (dicts, 2-tuples, etc.).

Each loader should have an ``is_usable`` attribute set. This is a boolean that
specifies whether the loader can be used with this Python installation. Each
loader is responsible for setting this when it is initialized.

This code is based on Django's template loader code: http://bit.ly/WWOLU3
"""

from collections import namedtuple

from twisted.python import log

from trigger.exceptions import ImproperlyConfigured, LoaderFailed
from trigger.utils.importlib import import_module
from trigger.conf import settings


# Exports
__all__ = ('BaseLoader', 'load_metadata')


# Classes
class BaseLoader(object):
    is_usable = False

    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, data_source, **kwargs):
        return self.load_data(data_source, **kwargs)

    def load_data(self, data_source, **kwargs):
        data = self.load_data_source(data_source, **kwargs)
        return data

    def load_data_source(self, data_source, **kwargs):
        """
        Returns an iterable of key/value pairs for the given ``data_source``.
        """
        raise NotImplementedError

    def reset(self):
        """
        Resets any state maintained by the loader instance.
        """
        pass


# Functions
def find_data_loader(loader):
    """
    Given a ``loader`` string/list/tuple, try to unpack, load it, and return the
    callable loader object.

    If ``loader`` is specified as string, treat it as the fully-qualified
    Python path to the callable Loader object.

    Optionally, if `loader`` is a list/tuple, the first item in the tuple should be the
    Loader's module path, and subsequent items are passed to the Loader object
    during initialization. This could be useful in initializing a custom Loader
    for a database backend, for example.

    :param loader:
        A string represnting the Python path to a Loader object, or list/tuple
        of loader path and args to pass to the Loader.
    """
    if isinstance(loader, (tuple, list)):
        loader, args = loader[0], loader[1:]
    else:
        args = []

    log.msg("BUILDING LOADER: %s; WITH ARGS: %s" % (loader, args))
    err_template = "Error importing data source loader %s: '%s'"
    if isinstance(loader, basestring):
        module, attr = loader.rsplit('.', 1)
        try:
            mod = import_module(module)
        except ImportError as err:
            raise ImproperlyConfigured(err_template % (loader, err))

        try:
            DataLoader = getattr(mod, attr)
        except AttributeError as err:
            raise ImproperlyConfigured(err_template % (loader, err))

        if hasattr(DataLoader, 'load_data_source'):
            func = DataLoader(*args)
        else:
            # Try loading module the old-fashioned way where string is full
            # path to callabale.
            if args:
                raise ImproperlyConfigured("Error importing data source loader %s: Can't pass arguments to function-based loader!" % loader)
            func = DataLoader

        if not func.is_usable:
            import warnings
            warnings.warn("Your NETDEVICES_LOADERS setting includes %r, but your Python installation doesn't support that type of data loading. Consider removing that line from NETDEVICES_LOADERS." % loader)
            return None
        else:
            return func
    else:
        raise ImproperlyConfigured('Loader does not define a "load_data" callable data source loader.')


#: Namedtuple that holds loader instance and device metadata
LoaderMetadata = namedtuple('LoaderMetadata', 'loader metadata')


def load_metadata(data_source, **kwargs):
    """
    Iterate thru data loaders to load metadata.

    Loaders should return an iterable of dict/2-tuples or ``None``. It will try
    each one until it can return data. The first one to return data wins.

    :param data_source:
        Typically a file path, but it can be any data format you desire that
        can be passed onto a Loader object to retrieve metadata.

    :param kwargs:
        Optional keyword arguments you wish to pass to the Loader.

    :returns:
        `~trigger.netdevices.loader.LoaderMetadata` instance
    """
    # Iterate and build a loader callables, call them, stop when we get data.
    tried = []
    log.msg('LOADING DATA FROM:', data_source)
    for loader_name in settings.NETDEVICES_LOADERS:
        loader = find_data_loader(loader_name)
        log.msg('TRYING LOADER:', loader)
        if loader is None:
            log.msg('CANNOT USE LOADER:', loader)
            continue

        try:
            # Pass the args to the loader!
            data = loader(data_source, **kwargs)
            log.msg('LOADER: SUCCESS!')
        except LoaderFailed as err:
            tried.append(loader)
            log.msg('LOADER - FAILURE: %s' % err)
            continue
        else:
            # Successfully parsed (we hope)
            if data is not None:
                log.msg('LOADERS TRIED: %r' % tried)
                return LoaderMetadata(loader, data)
            else:
                tried.append(loader)
                continue

    # All loaders failed. We don't want to get to this point!
    raise RuntimeError('No data loaders succeeded. Tried: %r' % tried)
