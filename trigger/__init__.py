__version__ = (1, 2, 3)

full_version = '.'.join(str(x) for x in __version__)
release = full_version
short_version = '.'.join(str(x) for x in __version__[0:3])
