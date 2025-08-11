"""
Looma - A comprehensive Python packaging and auto-update platform.

This package provides tools for packaging Python applications with multiple
engines (PyInstaller, Nuitka, cx_Freeze) and built-in auto-update capabilities.
"""

from looma.__version__ import __version__
from looma.core.config import ConfigManager
from looma.core.exceptions import LoomaError

__all__ = [
    "__version__",
    "ConfigManager",
    "LoomaError",
]