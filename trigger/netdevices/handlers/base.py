"""
NetDevice base handler for definining the interface.
"""

from abc import abstractproperty, abstractmethod, ABCMeta

from trigger import tacacsrc


class BaseHandler(object):
    __metaclass__ = ABCMeta

    def __init__(self, device, creds=None):
        self.device = device

        if creds is None:
            creds = tacacsrc.validate_credentials()
        self.creds = creds

        self._connected = False

        self.post_init()

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.name)

    @abstractproperty
    def name(self):
        pass

    def open(self, *args, **kwargs):
        self.perform_open(*args, **kwargs)
        self._connected = True
        return self._connected

    @abstractmethod
    def perform_open(self, *args, **kwargs):
        pass

    def close(self):
        self.perform_close()
        self._connected = False
        return

    @abstractmethod
    def perform_close(self):
        pass

    @property
    def connected(self):
        return self._connected

    @abstractmethod
    def post_init(self):
        """
        Overloadable method for post __init__

        Use this for things that need to happen post-init, including
        subclass-specific argument handling.

        This method is called at the very end of __init__ unless ``raw`` is
        given.

        :params kwargs: All unhandled kwargs from __init__ are passed here
        :type kwargs: dict
        """
        pass
