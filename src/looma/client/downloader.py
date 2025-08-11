"""Download manager for Looma update client."""

import asyncio
import hashlib
from pathlib import Path
from typing import Callable, Optional

import aiofiles
import httpx
import structlog

from looma.core.constants import (
    CONNECTION_TIMEOUT,
    DOWNLOAD_CHUNK_SIZE,
    DOWNLOAD_TIMEOUT,
    MAX_DOWNLOAD_SIZE,
    READ_TIMEOUT,
)
from looma.core.exceptions import NetworkError
from looma.core.utils import ensure_dir, format_size, get_temp_dir, verify_hash

logger = structlog.get_logger()


class Downloader:
    """
    Download manager with resume support and progress tracking.
    
    Attributes
    ----------
    config : dict
        Configuration
    client : httpx.AsyncClient
        HTTP client
    """
    
    def __init__(self, config):
        """
        Initialize downloader.
        
        Parameters
        ----------
        config : ConfigManager
            Configuration manager
        """
        self.config = config
        
        # Configure timeouts
        timeout = httpx.Timeout(
            connect=config.get("advanced.timeouts.connection", CONNECTION_TIMEOUT),
            read=config.get("advanced.timeouts.read", READ_TIMEOUT),
            write=None,
            pool=None,
        )
        
        # Configure proxy
        proxies = self._get_proxies()
        
        # Create HTTP client
        self.client = httpx.AsyncClient(
            timeout=timeout,
            proxies=proxies,
            follow_redirects=True,
            headers={"User-Agent": "Looma/1.0"},
        )
    
    def _get_proxies(self) -> dict:
        """
        Get proxy configuration.
        
        Returns
        -------
        dict
            Proxy configuration
        """
        proxy_config = self.config.get("advanced.proxy", {})
        proxies = {}
        
        if proxy_config.get("http"):
            proxies["http://"] = proxy_config["http"]
        if proxy_config.get("https"):
            proxies["https://"] = proxy_config["https"]
        
        return proxies
    
    async def download(
        self,
        url: str,
        dest_path: Optional[Path] = None,
        expected_hash: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
        resume: bool = True,
    ) -> Path:
        """
        Download a file with resume support.
        
        Parameters
        ----------
        url : str
            Download URL
        dest_path : Optional[Path]
            Destination path
        expected_hash : Optional[str]
            Expected file hash
        progress_callback : Optional[Callable]
            Progress callback function
        resume : bool
            Enable resume support
            
        Returns
        -------
        Path
            Path to downloaded file
            
        Raises
        ------
        NetworkError
            If download fails
        """
        # Determine destination path
        if not dest_path:
            filename = url.split("/")[-1].split("?")[0]
            dest_path = get_temp_dir() / filename
        
        dest_path = Path(dest_path)
        ensure_dir(dest_path.parent)
        
        # Check if file already exists
        if dest_path.exists() and expected_hash:
            if verify_hash(dest_path, expected_hash):
                logger.info(f"File already downloaded: {dest_path}")
                return dest_path
        
        try:
            # Get file info
            file_size = await self._get_file_size(url)
            
            if file_size and file_size > MAX_DOWNLOAD_SIZE:
                raise NetworkError(f"File too large: {format_size(file_size)}")
            
            # Check for partial download
            resume_pos = 0
            if resume and dest_path.exists():
                resume_pos = dest_path.stat().st_size
                if file_size and resume_pos >= file_size:
                    # Already complete
                    if expected_hash and not verify_hash(dest_path, expected_hash):
                        # Corrupted, restart
                        resume_pos = 0
                        dest_path.unlink()
                    else:
                        return dest_path
            
            # Download file
            await self._download_file(
                url,
                dest_path,
                resume_pos,
                file_size,
                progress_callback,
            )
            
            # Verify hash
            if expected_hash and not verify_hash(dest_path, expected_hash):
                dest_path.unlink()
                raise NetworkError("Downloaded file hash mismatch")
            
            logger.info(f"Downloaded successfully: {dest_path}")
            return dest_path
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise NetworkError(f"Download failed: {e}")
    
    async def _get_file_size(self, url: str) -> Optional[int]:
        """
        Get file size from server.
        
        Parameters
        ----------
        url : str
            File URL
            
        Returns
        -------
        Optional[int]
            File size in bytes
        """
        try:
            response = await self.client.head(url)
            if "content-length" in response.headers:
                return int(response.headers["content-length"])
        except Exception:
            pass
        return None
    
    async def _download_file(
        self,
        url: str,
        dest_path: Path,
        resume_pos: int,
        total_size: Optional[int],
        progress_callback: Optional[Callable],
    ) -> None:
        """
        Download file with progress tracking.
        
        Parameters
        ----------
        url : str
            Download URL
        dest_path : Path
            Destination path
        resume_pos : int
            Resume position
        total_size : Optional[int]
            Total file size
        progress_callback : Optional[Callable]
            Progress callback
        """
        headers = {}
        if resume_pos > 0:
            headers["Range"] = f"bytes={resume_pos}-"
        
        mode = "ab" if resume_pos > 0 else "wb"
        downloaded = resume_pos
        
        async with self.client.stream("GET", url, headers=headers) as response:
            response.raise_for_status()
            
            # Update total size if available
            if not total_size and "content-length" in response.headers:
                total_size = int(response.headers["content-length"]) + resume_pos
            
            async with aiofiles.open(dest_path, mode) as f:
                async for chunk in response.aiter_bytes(DOWNLOAD_CHUNK_SIZE):
                    await f.write(chunk)
                    downloaded += len(chunk)
                    
                    if progress_callback:
                        progress = (downloaded / total_size * 100) if total_size else 0
                        progress_callback(downloaded, total_size, progress)
    
    async def download_json(self, url: str) -> dict:
        """
        Download and parse JSON.
        
        Parameters
        ----------
        url : str
            JSON URL
            
        Returns
        -------
        dict
            Parsed JSON data
            
        Raises
        ------
        NetworkError
            If download or parsing fails
        """
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise NetworkError(f"Failed to download JSON: {e}")
    
    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()