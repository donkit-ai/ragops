__all__ = ["__version__"]

try:
    from importlib.metadata import PackageNotFoundError, version

    __version__ = version("donkit-ragops")
except PackageNotFoundError:
    __version__ = "unknown"
