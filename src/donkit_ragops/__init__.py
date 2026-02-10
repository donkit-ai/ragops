__all__ = ["__version__"]

# Hardcoded version for development
__version__ = "0.5.4"

# In production, try to get version from installed package
# but keep hardcoded version as fallback
try:
    from importlib.metadata import PackageNotFoundError, version
    try:
        installed_version = version("donkit-ragops")
        # Only use installed version if it's different from development version
        # This helps in development environments
    except PackageNotFoundError:
        pass
except ImportError:
    pass
