"""Base source interface for Looma update sources."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from looma.core.exceptions import NetworkError


class BaseSource(ABC):
    """
    Abstract base class for update sources.
    
    Attributes
    ----------
    config : dict
        Source configuration
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the source.
        
        Parameters
        ----------
        config : dict
            Source configuration
        """
        self.config = config
    
    @abstractmethod
    async def get_versions(self, channel: str) -> Dict[str, Any]:
        """
        Fetch available versions for channel.
        
        Parameters
        ----------
        channel : str
            Update channel (stable, beta, alpha, etc.)
            
        Returns
        -------
        dict
            Version information
            
        Raises
        ------
        NetworkError
            If fetching fails
        """
        pass
    
    @abstractmethod
    async def upload_release(
        self,
        version: str,
        files: List[str],
        channel: str = "stable",
        notes: str = "",
    ) -> None:
        """
        Upload release files to source.
        
        Parameters
        ----------
        version : str
            Version string
        files : List[str]
            List of file paths to upload
        channel : str
            Release channel
        notes : str
            Release notes
            
        Raises
        ------
        NetworkError
            If upload fails
        """
        pass
    
    async def get_latest_version(self, channel: str) -> Optional[str]:
        """
        Get latest version for channel.
        
        Parameters
        ----------
        channel : str
            Update channel
            
        Returns
        -------
        Optional[str]
            Latest version string or None
        """
        versions = await self.get_versions(channel)
        if not versions:
            return None
        
        # Find latest version
        from packaging import version
        latest = None
        
        for ver in versions.keys():
            if not latest or version.parse(ver) > version.parse(latest):
                latest = ver
        
        return latest
    
    async def get_version_info(self, version: str, channel: str) -> Optional[Dict[str, Any]]:
        """
        Get information for specific version.
        
        Parameters
        ----------
        version : str
            Version string
        channel : str
            Update channel
            
        Returns
        -------
        Optional[dict]
            Version information or None
        """
        versions = await self.get_versions(channel)
        return versions.get(version)
    
    def validate_config(self) -> bool:
        """
        Validate source configuration.
        
        Returns
        -------
        bool
            True if configuration is valid
            
        Raises
        ------
        NetworkError
            If configuration is invalid
        """
        return True