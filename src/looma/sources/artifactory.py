"""JFrog Artifactory source for Looma."""

from pathlib import Path
from typing import Any, Dict, List

import httpx
import structlog

from looma.core.exceptions import NetworkError
from looma.sources.base import BaseSource

logger = structlog.get_logger()


class ArtifactorySource(BaseSource):
    """
    JFrog Artifactory source implementation.
    
    Uses Artifactory REST API to manage releases.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Artifactory source.
        
        Parameters
        ----------
        config : dict
            Source configuration
        """
        super().__init__(config)
        self.url = config.get("url")
        self.repository = config.get("repository")
        self.username = config.get("username")
        self.password = config.get("password")
        self.api_key = config.get("api_key")
        
        if not self.url:
            raise NetworkError("Artifactory URL not configured")
        if not self.repository:
            raise NetworkError("Artifactory repository not configured")
        
        # Ensure URL ends without slash
        self.url = self.url.rstrip("/")
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers.
        
        Returns
        -------
        dict
            Authentication headers
        """
        headers = {}
        
        if self.api_key:
            headers["X-JFrog-Art-Api"] = self.api_key
        elif self.username and self.password:
            import base64
            auth_str = f"{self.username}:{self.password}"
            auth_bytes = auth_str.encode("ascii")
            auth_b64 = base64.b64encode(auth_bytes).decode("ascii")
            headers["Authorization"] = f"Basic {auth_b64}"
        
        return headers
    
    async def get_versions(self, channel: str) -> Dict[str, Any]:
        """
        Fetch available versions from Artifactory.
        
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
            # Get versions.json from Artifactory
            versions_url = f"{self.url}/artifactory/{self.repository}/looma/{channel}/versions.json"
            
            headers = self._get_auth_headers()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(versions_url, headers=headers)
                
                if response.status_code == 404:
                    logger.warning(f"versions.json not found for channel {channel}")
                    return {}
                
                response.raise_for_status()
                data = response.json()
                
                return data.get("versions", {})
                
        except Exception as e:
            logger.error(f"Failed to fetch versions from Artifactory: {e}")
            raise NetworkError(f"Failed to fetch versions: {e}")
    
    async def upload_release(
        self,
        version: str,
        files: List[str],
        channel: str = "stable",
        notes: str = "",
    ) -> None:
        """
        Upload release to Artifactory.
        
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
        """
        try:
            # Upload each file to Artifactory
            for file_path in files:
                await self._upload_file(version, file_path, channel)
            
            # Update versions.json
            await self._update_versions_json(version, files, channel, notes)
            
            # Set properties on uploaded files
            await self._set_properties(version, files, channel)
            
            logger.info(f"Successfully uploaded release {version} to Artifactory")
            
        except Exception as e:
            logger.error(f"Failed to upload release: {e}")
            raise NetworkError(f"Failed to upload release: {e}")
    
    async def _upload_file(self, version: str, file_path: str, channel: str) -> None:
        """
        Upload file to Artifactory.
        
        Parameters
        ----------
        version : str
            Version string
        file_path : str
            Path to file
        channel : str
            Release channel
        """
        file_path = Path(file_path)
        target_path = f"looma/{channel}/{version}/{file_path.name}"
        upload_url = f"{self.url}/artifactory/{self.repository}/{target_path}"
        
        headers = self._get_auth_headers()
        
        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as f:
                response = await client.put(
                    upload_url,
                    headers=headers,
                    content=f.read(),
                    timeout=300,
                )
                response.raise_for_status()
    
    async def _update_versions_json(
        self,
        version: str,
        files: List[str],
        channel: str,
        notes: str,
    ) -> None:
        """
        Update versions.json in Artifactory.
        
        Parameters
        ----------
        version : str
            Version string
        files : List[str]
            Uploaded files
        channel : str
            Release channel
        notes : str
            Release notes
        """
        import json
        from datetime import datetime, timezone
        
        # Download existing versions.json
        existing_data = {"versions": {}}
        
        versions_url = f"{self.url}/artifactory/{self.repository}/looma/{channel}/versions.json"
        headers = self._get_auth_headers()
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(versions_url, headers=headers)
                if response.status_code == 200:
                    existing_data = response.json()
            except Exception:
                pass
            
            # Update with new version
            version_info = {
                "notes": notes,
                "pub_date": datetime.now(timezone.utc).isoformat(),
                "platforms": {},
            }
            
            # Add platform files
            for file_path in files:
                platform_info = self._parse_platform_from_filename(file_path)
                if platform_info:
                    platform, arch = platform_info
                    platform_key = f"{platform}-{arch}"
                    
                    file_name = Path(file_path).name
                    download_url = f"{self.url}/artifactory/{self.repository}/looma/{channel}/{version}/{file_name}"
                    
                    version_info["platforms"][platform_key] = {
                        "url": download_url,
                        "size": Path(file_path).stat().st_size,
                        "hash": self._calculate_hash(file_path),
                        "signature": "",  # Would be calculated separately
                    }
            
            existing_data["versions"][version] = version_info
            
            # Upload updated versions.json
            response = await client.put(
                versions_url,
                headers=headers,
                content=json.dumps(existing_data, indent=2),
            )
            response.raise_for_status()
    
    async def _set_properties(self, version: str, files: List[str], channel: str) -> None:
        """
        Set properties on uploaded artifacts.
        
        Parameters
        ----------
        version : str
            Version string
        files : List[str]
            Uploaded files
        channel : str
            Release channel
        """
        headers = self._get_auth_headers()
        
        async with httpx.AsyncClient() as client:
            for file_path in files:
                file_name = Path(file_path).name
                artifact_path = f"{self.repository}/looma/{channel}/{version}/{file_name}"
                props_url = f"{self.url}/artifactory/api/storage/{artifact_path}"
                
                properties = {
                    "looma.version": version,
                    "looma.channel": channel,
                }
                
                # Add platform properties
                platform_info = self._parse_platform_from_filename(file_path)
                if platform_info:
                    platform, arch = platform_info
                    properties["looma.platform"] = platform
                    properties["looma.arch"] = arch
                
                # Build properties string
                props_str = ";".join([f"{k}={v}" for k, v in properties.items()])
                
                response = await client.put(
                    f"{props_url}?properties={props_str}",
                    headers=headers,
                )
                
                if response.status_code not in [200, 204]:
                    logger.warning(f"Failed to set properties on {file_name}")
    
    def _parse_platform_from_filename(self, filename: str) -> tuple:
        """
        Parse platform from filename.
        
        Parameters
        ----------
        filename : str
            File name
            
        Returns
        -------
        tuple
            (platform, architecture) or None
        """
        filename_lower = Path(filename).name.lower()
        
        if "win" in filename_lower:
            return ("windows", "win64" if "64" in filename_lower else "win32")
        elif "mac" in filename_lower or "darwin" in filename_lower:
            return ("macos", "arm64" if "arm" in filename_lower else "x64")
        elif "linux" in filename_lower:
            return ("linux", "arm64" if "arm" in filename_lower else "x64")
        
        return None
    
    def _calculate_hash(self, file_path: str) -> str:
        """
        Calculate file hash.
        
        Parameters
        ----------
        file_path : str
            Path to file
            
        Returns
        -------
        str
            SHA256 hash
        """
        import hashlib
        
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        
        return f"sha256:{hasher.hexdigest()}"