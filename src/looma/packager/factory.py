"""Packager factory for creating packaging engine instances."""

from typing import Dict, Type

from looma.core.constants import (
    ENGINE_CXFREEZE,
    ENGINE_NUITKA,
    ENGINE_PYINSTALLER,
)
from looma.core.exceptions import PackagingError
from looma.packager.base import BasePackager


class PackagerFactory:
    """
    Factory for creating packager instances.

    Attributes
    ----------
    packagers : dict
        Registry of available packagers
    """

    def __init__(self):
        """Initialize the packager factory."""
        self.packagers: Dict[str, Type[BasePackager]] = {}
        self._register_default_packagers()

    def _register_default_packagers(self) -> None:
        """Register default packaging engines."""
        # Import here to avoid circular dependencies
        from looma.packager.pyinstaller import PyInstallerPackager
        from looma.packager.nuitka import NuitkaPackager
        from looma.packager.cxfreeze import CxFreezePackager

        self.register(ENGINE_PYINSTALLER, PyInstallerPackager)
        self.register(ENGINE_NUITKA, NuitkaPackager)
        self.register(ENGINE_CXFREEZE, CxFreezePackager)

    def register(self, name: str, packager_class: Type[BasePackager]) -> None:
        """
        Register a new packager engine.

        Parameters
        ----------
        name : str
            Packager name
        packager_class : Type[BasePackager]
            Packager class
        """
        self.packagers[name] = packager_class

    def create(self, name: str, config: Dict) -> BasePackager:
        """
        Create and configure a packager instance.

        Parameters
        ----------
        name : str
            Packager name
        config : dict
            Configuration dictionary

        Returns
        -------
        BasePackager
            Configured packager instance

        Raises
        ------
        PackagingError
            If packager is not found
        """
        if name not in self.packagers:
            available = ", ".join(self.packagers.keys())
            raise PackagingError(
                f"Unknown packager: {name}. Available: {available}"
            )

        packager_class = self.packagers[name]
        return packager_class(config)

    def list_packagers(self) -> list:
        """
        List available packagers.

        Returns
        -------
        list
            List of packager names
        """
        return list(self.packagers.keys())

    def get_packager_class(self, name: str) -> Type[BasePackager]:
        """
        Get packager class by name.

        Parameters
        ----------
        name : str
            Packager name

        Returns
        -------
        Type[BasePackager]
            Packager class

        Raises
        ------
        PackagingError
            If packager is not found
        """
        if name not in self.packagers:
            available = ", ".join(self.packagers.keys())
            raise PackagingError(
                f"Unknown packager: {name}. Available: {available}"
            )
        return self.packagers[name]
    
    def is_available(self, name: str) -> bool:
        """
        Check if a packager is available.

        Parameters
        ----------
        name : str
            Packager name

        Returns
        -------
        bool
            True if packager is available
        """
        if name not in self.packagers:
            return False

        # Check if the packager's dependencies are installed
        try:
            packager_class = self.packagers[name]
            # Create a minimal config that won't cause issues
            dummy_config = {
                "packaging": {"entry_point": "main.py"},
                "build": {"output_dir": "dist", "build_dir": "build"}
            }
            packager = packager_class(dummy_config)
            return packager.is_installed()
        except Exception:
            return False


# Global factory instance
packager_factory = PackagerFactory()
