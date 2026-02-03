from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("trigger")
except PackageNotFoundError:
    # Package is not installed (development mode)
    __version__ = "2.0.0.dev0"
