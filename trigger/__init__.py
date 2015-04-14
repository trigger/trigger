__version__ = (1, 5, 2, 'b1')

full_version = '.'.join(str(x) for x in __version__[0:3]) + \
               ''.join(__version__[3:])
release = full_version
short_version = '.'.join(str(x) for x in __version__[0:3])
