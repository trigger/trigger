"""
NetDevice driver base.
"""

from abc import abstractproperty, abstractmethod, ABCMeta


class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass


class DriverRegistry(object):
    def __init__(self):
        self._registry = {}

    def register(self, driver):
        if not issubclass(driver, BaseDriver):
            raise RuntimeError('Drivers must be a subclass of BaseDriver')

        if driver in self._registry:
            raise AlreadyRegistered(
                'The driver %s is already registered' % driver.__name__
            )

        driver_obj = driver()
        self._registry[driver.name] = driver_obj

    def is_registered(self, driver):
        return driver.name in self._registry

    @property
    def drivers(self):
        return self._registry

    def get_driver(self, name):
        if name not in self._registry:
            raise NotRegistered(
                'The driver %s is not registered' % name
            )

        return self._registry[name]


class BaseDriver(object):
    __metaclass__ = ABCMeta

    delimiter = '\n'

    def __init__(self):
        self.post_init()
        self.title = self.name.title()
        self.post_init()

        # registry.register(self.__class__)

    def __repr__(self):
        return '<%s>' % self.__class__.__name__

    @abstractmethod
    def post_init(self):
        """
        Overloadable method which is called after __init__.
        """
        pass

    @abstractproperty
    def name(self):
        pass

    @abstractproperty
    def prompt_pattern(self):
        pass

    @abstractproperty
    def startup_commands(self):
        pass

    @abstractproperty
    def commit_commands(self):
        pass

    @abstractproperty
    def default_type(self):
        pass

    @abstractproperty
    def supported_types(self):
        pass


registry = DriverRegistry()
