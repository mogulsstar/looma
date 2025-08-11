"""GitHub Release source for Looma."""

import json
from pathlib import Path
from typing import Any, Dict, List

import httpx
import structlog

from looma.core.exceptions import NetworkError
from looma.sources.base import BaseSource

logger = structlog.get_logger()


class GitHubSource(BaseSource):
    """
    GitHub Release source implementation.
    
    Uses GitHub API to fetch and upload releases.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize GitHub source.
        
        Parameters
        ----------
        config : dict
            Source configuration with repo and token
        """
        super().__init__(config)
        self.repo = config.get("repo")
        self.token = config.get("token")
        self.api_base = "https://api.github.com"
        
        if not self.repo:
            raise NetworkError("GitHub repo not configured")
    
    async def get_versions(self, channel: str) -> Dict[str, Any]:
        """
        Fetch available versions from GitHub releases.
        
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
            # Fetch releases from GitHub
            releases = await self._get_releases()
            
            # Parse versions.json from latest release
            versions_data = await self._get_versions_json(releases, channel)
            
            return versions_data
            
        except Exception as e:
            logger.error(f"Failed to fetch versions from GitHub: {e}")
            raise NetworkError(f"Failed to fetch versions: {e}")
    
    async def _get_releases(self) -> List[Dict[str, Any]]:
        """
        Get releases from GitHub API.
        
        Returns
        -------
        List[dict]
            List of release data
        """
        url = f"{self.api_base}/repos/{self.repo}/releases"
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def _get_versions_json(self, releases: List[Dict], channel: str) -> Dict[str, Any]:
        """
        Get versions.json from releases.
        
        Parameters
        ----------
        releases : List[dict]
            GitHub releases
        channel : str
            Update channel
            
        Returns
        -------
        dict
            Parsed versions data
        """
        # Look for versions.json asset in releases
        for release in releases:
            assets = release.get("assets", [])
            
            for asset in assets:
                if asset["name"] == "versions.json":
                    # Download and parse versions.json
                    url = asset["browser_download_url"]
                    
                    async with httpx.AsyncClient() as client:
                        response = await client.get(url)
                        response.raise_for_status()
                        data = response.json()
                        
                        # Return channel-specific data
                        channels = data.get("channels", {})
                        return channels.get(channel, {}).get("versions", {})
        
        # Fallback: construct from release data
        return self._construct_versions_from_releases(releases, channel)
    
    def _construct_versions_from_releases(self, releases: List[Dict], channel: str) -> Dict[str, Any]:
        """
        Construct version data from releases.
        
        Parameters
        ----------
        releases : List[dict]
            GitHub releases
        channel : str
            Update channel
            
        Returns
        -------
        dict
            Version data
        """
        versions = {}
        
        for release in releases:
            # Skip drafts and pre-releases for stable channel
            if channel == "stable" and (release.get("draft") or release.get("prerelease")):
                continue
            
            # Skip stable releases for beta/alpha channels
            if channel != "stable" and not release.get("prerelease"):
                continue
            
            version = release["tag_name"].lstrip("v")
            
            # Find platform assets
            platforms = {}
            for asset in release.get("assets", []):
                platform_info = self._parse_asset_platform(asset["name"])
                if platform_info:
                    platform, arch = platform_info
                    platform_key = f"{platform}-{arch}"
                    
                    platforms[platform_key] = {
                        "url": asset["browser_download_url"],
                        "size": asset["size"],
                        "hash": "",  # Would need to be stored separately
                        "signature": "",  # Would need to be stored separately
                    }
            
            if platforms:
                versions[version] = {
                    "notes": release.get("body", ""),
                    "pub_date": release["published_at"],
                    "platforms": platforms,
                }
        
        return versions
    
    def _parse_asset_platform(self, filename: str) -> tuple:
        """
        Parse platform from asset filename.
        
        Parameters
        ----------
        filename : str
            Asset filename
            
        Returns
        -------
        tuple
            (platform, architecture) or None
        """
        filename_lower = filename.lower()
        
        # Windows
        if "win" in filename_lower or ".exe" in filename_lower:
            if "64" in filename_lower or "x64" in filename_lower:
                return ("windows", "win64")
            elif "32" in filename_lower or "x86" in filename_lower:
                return ("windows", "win32")
            else:
                return ("windows", "win64")  # Default to 64-bit
        
        # macOS
        elif "mac" in filename_lower or "darwin" in filename_lower or ".dmg" in filename_lower:
            if "arm" in filename_lower or "m1" in filename_lower:
                return ("macos", "arm64")
            else:
                return ("macos", "x64")
        
        # Linux
        elif "linux" in filename_lower or ".appimage" in filename_lower:
            if "arm" in filename_lower:
                return ("linux", "arm64")
            else:
                return ("linux", "x64")
        
        return None
    
    async def upload_release(
        self,
        version: str,
        files: List[str],
        channel: str = "stable",
        notes: str = "",
    ) -> None:
        """
        Upload release to GitHub.
        
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
            # Create release
            release = await self._create_release(version, channel, notes)
            
            # Upload assets
            for file_path in files:
                await self._upload_asset(release["id"], file_path)
            
            # Upload versions.json
            await self._update_versions_json(version, files, channel, notes)
            
            logger.info(f"Successfully uploaded release {version} to GitHub")
            
        except Exception as e:
            logger.error(f"Failed to upload release: {e}")
            raise NetworkError(f"Failed to upload release: {e}")
    
    async def _create_release(self, version: str, channel: str, notes: str) -> Dict[str, Any]:
        """
        Create GitHub release.
        
        Parameters
        ----------
        version : str
            Version string
        channel : str
            Release channel
        notes : str
            Release notes
            
        Returns
        -------
        dict
            Created release data
        """
        url = f"{self.api_base}/repos/{self.repo}/releases"
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {self.token}",
        }
        
        data = {
            "tag_name": f"v{version}",
            "name": f"Release {version}",
            "body": notes,
            "draft": False,
            "prerelease": channel != "stable",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
    
    async def _upload_asset(self, release_id: int, file_path: str) -> None:
        """
        Upload asset to release.
        
        Parameters
        ----------
        release_id : int
            GitHub release ID
        file_path : str
            Path to file to upload
        """
        file_path = Path(file_path)
        url = f"{self.api_base.replace('api.', 'uploads.')}/repos/{self.repo}/releases/{release_id}/assets"
        
        headers = {
            "Authorization": f"token {self.token}",
            "Content-Type": "application/octet-stream",
        }
        
        params = {"name": file_path.name}
        
        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as f:
                response = await client.post(
                    url,
                    headers=headers,
                    params=params,
                    content=f.read(),
                    timeout=300,  # 5 minutes for large files
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
        Update versions.json file.
        
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
        # This would typically update a versions.json file
        # and upload it to the release
        pass