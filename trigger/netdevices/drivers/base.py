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

        self._registry[driver.name] = driver

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

    def __init__(self, hostname, username, password, port=None):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.post_init()

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.hostname)

    @abstractmethod
    def post_init(self):
        """
        Overloadable method which is called after __init__.
        """
        pass

    @abstractproperty
    def name(self):
        pass

    @property
    def title(self):
        return self.name.title()

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


registry = DriverRegistry()
