__version__ = (1, 4, 1, 'b2')

full_version = '.'.join(map(str, __version__[0:3])) + ''.join(__version__[3:])
release = full_version
short_version = '.'.join(str(x) for x in __version__[0:3])
