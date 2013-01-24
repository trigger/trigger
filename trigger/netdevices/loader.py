"""
Wrapper for loading metadata from storage of some sort (e.g. filesystem,
database)

This uses NETDEVICE_LOADERS settings, which is a list of loaders to use.
Each loader is expected to have this interface:

    callable(data_source, **kwargs)

``data_source`` is typically a file path from which to load the metadata, but can
be also be a list/tuple of [data_source, *args]
``kwargs`` are any optional keyword arguments you wish to send along.

The loader must return an iterable of key/value pairs (dicts, 2-tuples, etc.).

Each loader should have an ``is_usable`` attribute set. This is a boolean that
specifies whether the loader can be used with this Python installation. Each
loader is responsible for setting this when it is initialized.

For example, the eggs oader (which is capable of loading metadata from Python
eggs) sets ``is_usable`` to ``False`` if the "pkg_resources" module isn't
installed, beacuse this module is required to read eggs.
"""

from trigger.exceptions import ImproperlyConfigured, LoaderFailed
from trigger.utils.importlib import import_module
from trigger.conf import settings


class BaseLoader(object):
    is_usable = False
    format = None

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

def find_data_loader(loader):
    """
    Given a loader string/list/tuple, try to unpack, load it, and return the
    callable loader object.
    """
    if isinstance(loader, (tuple, list)):
        loader, args = loader[0], loader[1:]
    else:
        args = []

    print "TRYING LOADER:", loader
    print "    WITH ARGS:", args
    if isinstance(loader, basestring):
        module, attr = loader.rsplit('.', 1)
        try:
            mod = import_module(module)
        except ImportError as err:
            raise ImproperlyConfigured("Error importing data source loader %s: '%s'" % (loader, err))

        try:
            DataLoader = getattr(mod, attr)
        except AttributeError as err:
            raise ImproperlyConfigured("Error importing data source loader %s: '%s'" % (loader, err))

        if hasattr(DataLoader, 'load_data_source'):
            func = DataLoader(*args)
        else:
            # Try loading module the old-fashioned way where string is full
            # path to callabale.
            if args:
                raise ImproperlyConfigured("Error importing data source loader:%s: Can't pass arguments to function-based loader!" % loader)
            func = DataLoader

        if not func.is_usable:
            import warnings
            warnings.warn("Your NETDEVICES_LOADERS settings includes %r, but your Python installation doesn't support that type of data loading. Consider removing that line from NETDEVICES_LOADERS." % loader)
            return None
        else:
            return func
    else:
        raise ImproperlyConfigured('Loader does not define a "load_data" callable data source loader.')

def load_metadata(data_source, **kwargs):
    """
    Iterate thru data loaders to load metadata.

    Loaders should return an iterable of dict/2-tuples or ``None``. It will try
    each one until it can return data. The first one to return data wins. 
    """
    # Build a list of valid loader callables
    loaders = []
    for loader_name in settings.NETDEVICES_LOADERS:
        loader = find_data_loader(loader_name)
        if loader is not None:
            loaders.append(loader)

    # Iterate them and stop when you get data
    tried = []
    print '\nLOADING DATA FROM:', data_source
    for loader in loaders:
        print '\nTrying', loader
        try:
            # Pass the args to the loader!
            data = loader(data_source, **kwargs)
            print 'success!'
        except LoaderFailed as err:
            tried.append(loader)
            print '*** failure: %s' % err
            continue
        else:
            if data is not None:
                print '*** RETURNING RESULTS'
                print '*** here is what we tried', tried
                return data # Successfully parsed (we hope)
            else:
                tried.append(loader)
                continue 

    # We don't want to get to this point!
    raise RuntimeError('No data loaders succeeded. Tried: %r' % tried)

'''
def get_data(data_format):
    data = find_template(data_format)
    return data
'''
