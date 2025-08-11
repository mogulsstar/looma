"""Generic HTTP/HTTPS source for Looma."""

from typing import Any, Dict, List

import httpx
import structlog

from looma.core.exceptions import NetworkError
from looma.sources.base import BaseSource

logger = structlog.get_logger()


class HttpSource(BaseSource):
    """
    Generic HTTP/HTTPS source implementation.
    
    Fetches versions from a static HTTP endpoint.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize HTTP source.
        
        Parameters
        ----------
        config : dict
            Source configuration
        """
        super().__init__(config)
        self.base_url = config.get("base_url")
        self.auth_header = config.get("auth_header")
        
        if not self.base_url:
            raise NetworkError("HTTP base URL not configured")
        
        # Ensure URL ends without slash
        self.base_url = self.base_url.rstrip("/")
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get request headers.
        
        Returns
        -------
        dict
            Request headers
        """
        headers = {
            "Accept": "application/json",
            "User-Agent": "Looma/1.0",
        }
        
        if self.auth_header:
            # Support Bearer token or custom auth header
            if self.auth_header.startswith("Bearer "):
                headers["Authorization"] = self.auth_header
            else:
                # Assume it's a custom header in format "Header: Value"
                if ":" in self.auth_header:
                    header_name, header_value = self.auth_header.split(":", 1)
                    headers[header_name.strip()] = header_value.strip()
        
        return headers
    
    async def get_versions(self, channel: str) -> Dict[str, Any]:
        """
        Fetch available versions from HTTP endpoint.
        
        Parameters
        ----------
        channel : str
            Update channel
            
        Returns
        -------
        dict
            Version information
        """
        try:
            # Construct URL for versions.json
            versions_url = f"{self.base_url}/versions.json"
            
            headers = self._get_headers()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    versions_url,
                    headers=headers,
                    follow_redirects=True,
                )
                
                if response.status_code == 404:
                    logger.warning(f"versions.json not found at {versions_url}")
                    return {}
                
                response.raise_for_status()
                data = response.json()
                
                # Return channel-specific data
                channels = data.get("channels", {})
                channel_data = channels.get(channel, {})
                
                return channel_data.get("versions", {})
                
        except Exception as e:
            logger.error(f"Failed to fetch versions from HTTP source: {e}")
            raise NetworkError(f"Failed to fetch versions: {e}")
    
    async def upload_release(
        self,
        version: str,
        files: List[str],
        channel: str = "stable",
        notes: str = "",
    ) -> None:
        """
        Upload release to HTTP endpoint.
        
        Note: This is typically not supported for static HTTP sources.
        The files would need to be uploaded separately via FTP, SCP, etc.
        
        Parameters
        ----------
        version : str
            Version string
        files : List[str]
            Files to upload
        channel : str
            Release channel
        notes : str
            Release notes
            
        Raises
        ------
        NetworkError
            Always raised as HTTP sources are typically read-only
        """
        raise NetworkError(
            "HTTP source does not support direct uploads. "
            "Please upload files manually to your web server."
        )
    
    async def verify_connectivity(self) -> bool:
        """
        Verify connectivity to HTTP source.
        
        Returns
        -------
        bool
            True if source is reachable
        """
        try:
            headers = self._get_headers()
            
            async with httpx.AsyncClient() as client:
                response = await client.head(
                    self.base_url,
                    headers=headers,
                    follow_redirects=True,
                    timeout=10,
                )
                
                return response.status_code < 500
                
        except Exception as e:
            logger.error(f"Failed to verify connectivity: {e}")
            return False
    
    async def get_file_url(self, version: str, filename: str, channel: str = "stable") -> str:
        """
        Get direct download URL for a file.
        
        Parameters
        ----------
        version : str
            Version string
        filename : str
            File name
        channel : str
            Release channel
            
        Returns
        -------
        str
            Download URL
        """
        # Construct download URL based on common patterns
        # This can be customized based on server structure
        return f"{self.base_url}/{channel}/{version}/{filename}"
    
    async def get_metadata(self, version: str, channel: str = "stable") -> Dict[str, Any]:
        """
        Get metadata for a specific version.
        
        Parameters
        ----------
        version : str
            Version string
        channel : str
            Release channel
            
        Returns
        -------
        dict
            Version metadata
        """
        versions = await self.get_versions(channel)
        return versions.get(version, {})