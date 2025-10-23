"""ts-topy: A Python-based monitoring tool for Teraslice clusters."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("ts-topy")
except PackageNotFoundError:
    __version__ = "unknown"
