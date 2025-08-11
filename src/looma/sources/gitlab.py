"""GitLab Package Registry source for Looma."""

from typing import Any, Dict, List

import httpx
import structlog

from looma.core.exceptions import NetworkError
from looma.sources.base import BaseSource

logger = structlog.get_logger()


class GitLabSource(BaseSource):
    """
    GitLab Package Registry source implementation.
    
    Uses GitLab API to fetch and upload releases.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize GitLab source.
        
        Parameters
        ----------
        config : dict
            Source configuration
        """
        super().__init__(config)
        self.project_id = config.get("project_id")
        self.token = config.get("token")
        self.base_url = config.get("base_url", "https://gitlab.com")
        self.api_base = f"{self.base_url}/api/v4"
        
        if not self.project_id:
            raise NetworkError("GitLab project ID not configured")
        if not self.token:
            raise NetworkError("GitLab token not configured")
    
    async def get_versions(self, channel: str) -> Dict[str, Any]:
        """
        Fetch available versions from GitLab.
        
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
            # Get package files from GitLab
            packages = await self._get_packages()
            
            # Get versions.json from package registry
            versions_data = await self._get_versions_json(channel)
            
            if not versions_data:
                # Construct from package data
                versions_data = self._construct_versions_from_packages(packages, channel)
            
            return versions_data
            
        except Exception as e:
            logger.error(f"Failed to fetch versions from GitLab: {e}")
            raise NetworkError(f"Failed to fetch versions: {e}")
    
    async def _get_packages(self) -> List[Dict[str, Any]]:
        """
        Get packages from GitLab Package Registry.
        
        Returns
        -------
        List[dict]
            List of package data
        """
        url = f"{self.api_base}/projects/{self.project_id}/packages"
        
        headers = {
            "PRIVATE-TOKEN": self.token,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def _get_versions_json(self, channel: str) -> Dict[str, Any]:
        """
        Get versions.json from package registry.
        
        Parameters
        ----------
        channel : str
            Update channel
            
        Returns
        -------
        dict
            Parsed versions data
        """
        # Look for versions.json in generic packages
        url = f"{self.api_base}/projects/{self.project_id}/packages/generic/looma-versions/latest/versions.json"
        
        headers = {
            "PRIVATE-TOKEN": self.token,
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    channels = data.get("channels", {})
                    return channels.get(channel, {}).get("versions", {})
        except Exception:
            pass
        
        return {}
    
    def _construct_versions_from_packages(self, packages: List[Dict], channel: str) -> Dict[str, Any]:
        """
        Construct version data from packages.
        
        Parameters
        ----------
        packages : List[dict]
            GitLab packages
        channel : str
            Update channel
            
        Returns
        -------
        dict
            Version data
        """
        versions = {}
        
        for package in packages:
            # Filter by package type and channel
            if package.get("package_type") != "generic":
                continue
            
            if channel not in package.get("name", ""):
                continue
            
            version = package.get("version")
            if not version:
                continue
            
            # Get package files
            files_url = f"{self.api_base}/projects/{self.project_id}/packages/{package['id']}/package_files"
            
            # This would need to be async in real implementation
            # For now, we'll just structure the data
            versions[version] = {
                "notes": "",
                "pub_date": package.get("created_at", ""),
                "platforms": {},
            }
        
        return versions
    
    async def upload_release(
        self,
        version: str,
        files: List[str],
        channel: str = "stable",
        notes: str = "",
    ) -> None:
        """
        Upload release to GitLab Package Registry.
        
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
            # Upload each file to package registry
            for file_path in files:
                await self._upload_package_file(version, file_path, channel)
            
            # Update versions.json
            await self._update_versions_json(version, files, channel, notes)
            
            logger.info(f"Successfully uploaded release {version} to GitLab")
            
        except Exception as e:
            logger.error(f"Failed to upload release: {e}")
            raise NetworkError(f"Failed to upload release: {e}")
    
    async def _upload_package_file(self, version: str, file_path: str, channel: str) -> None:
        """
        Upload file to GitLab Package Registry.
        
        Parameters
        ----------
        version : str
            Version string
        file_path : str
            Path to file
        channel : str
            Release channel
        """
        from pathlib import Path
        
        file_path = Path(file_path)
        package_name = f"looma-{channel}"
        
        url = (
            f"{self.api_base}/projects/{self.project_id}/packages/generic/"
            f"{package_name}/{version}/{file_path.name}"
        )
        
        headers = {
            "PRIVATE-TOKEN": self.token,
        }
        
        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as f:
                response = await client.put(
                    url,
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
        Update versions.json in package registry.
        
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
        # Download existing versions.json
        existing_data = {}
        try:
            existing_data = await self._get_versions_json(channel)
        except Exception:
            pass
        
        # Update with new version
        # This would be implemented to update the versions.json
        # and upload it back to the package registry
        pass