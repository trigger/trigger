"""
NetDevice base dispatcher for definining the interface.
"""

from abc import abstractproperty, abstractmethod, ABCMeta

from trigger import tacacsrc


class BaseDispatcher(object):
    __metaclass__ = ABCMeta

    def __init__(self, device, creds=None):
        self.device = device

        # FIXME(jathan): Move credentials to NetDevice object.
        if creds is None:
            creds = tacacsrc.validate_credentials()
        self.creds = creds

        self.driver = self.get_driver()

    def __repr__(self):
        return '<%s>' % self.__class__.__name__

    @abstractmethod
    def driver_connected(self):
        pass

    @abstractmethod
    def get_driver(self):
        """This is how you tell the dispatcher to get a driver."""
        pass

    def dispatch(self, method_name, *args, **kwargs):
        driver = self.driver
        method = getattr(driver, method_name)

        print 'Calling %s on %s w/ args=%r, kwargs=%r' % (
            method_name, driver, args, kwargs
        )

        return method(*args, **kwargs)
