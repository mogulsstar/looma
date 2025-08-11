"""Main update client for Looma."""

import asyncio
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
import structlog

from looma.client.downloader import Downloader
from looma.client.ui import UpdateDialog
from looma.client.verifier import SignatureVerifier
from looma.core.config import ConfigManager
from looma.core.constants import (
    CHANNEL_STABLE,
    DEFAULT_CHECK_INTERVAL,
    STRATEGY_FORCE,
    STRATEGY_PROMPT,
    STRATEGY_SILENT,
)
from looma.core.exceptions import UpdateError
from looma.core.utils import (
    compare_versions,
    ensure_dir,
    get_platform,
    is_newer_version,
    restart_application,
)

logger = structlog.get_logger()


class UpdateInfo:
    """
    Update information container.
    
    Attributes
    ----------
    version : str
        Version string
    notes : str
        Release notes
    url : str
        Download URL
    size : int
        Package size in bytes
    hash : str
        SHA256 hash
    signature : str
        Ed25519 signature
    delta_url : Optional[str]
        Delta update URL if available
    pub_date : datetime
        Publication date
    """
    
    def __init__(self, data: Dict[str, Any]):
        """
        Initialize update info.
        
        Parameters
        ----------
        data : dict
            Update data
        """
        self.version = data.get("version", "")
        self.notes = data.get("notes", "")
        self.url = data.get("url", "")
        self.size = data.get("size", 0)
        self.hash = data.get("hash", "")
        self.signature = data.get("signature", "")
        self.delta_url = data.get("delta", {}).get("url")
        self.delta_size = data.get("delta", {}).get("size", 0)
        self.delta_hash = data.get("delta", {}).get("hash")
        
        # Parse publication date
        pub_date_str = data.get("pub_date", "")
        if pub_date_str:
            self.pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
        else:
            self.pub_date = datetime.now()
    
    def should_use_delta(self, threshold: int) -> bool:
        """
        Check if delta update should be used.
        
        Parameters
        ----------
        threshold : int
            Size threshold for delta updates
            
        Returns
        -------
        bool
            True if delta should be used
        """
        if not self.delta_url:
            return False
        
        return self.size > threshold and self.delta_size < self.size


class UpdateClient:
    """
    Main update client for checking and applying updates.
    
    Attributes
    ----------
    config : ConfigManager
        Configuration manager
    source : BaseSource
        Update source interface
    downloader : Downloader
        Download manager
    verifier : SignatureVerifier
        Signature verification
    check_thread : Optional[threading.Thread]
        Background check thread
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize update client.
        
        Parameters
        ----------
        config_path : Optional[Path]
            Path to configuration file
        """
        self.config = ConfigManager(config_path)
        self.config.load()
        
        # Initialize components
        self.downloader = Downloader(self.config)
        self.verifier = SignatureVerifier(self.config)
        
        # Initialize source
        self.source = self._init_source()
        
        # State
        self.check_thread = None
        self.last_check = None
        self.skip_version = None
        self.remind_later_until = None
    
    def _init_source(self):
        """
        Initialize update source.
        
        Returns
        -------
        BaseSource
            Configured update source
        """
        from looma.sources import source_factory
        
        source_config = self.config.get("update.source", {})
        source_type = source_config.get("type")
        
        if not source_type:
            raise UpdateError("Update source not configured")
        
        return source_factory.create(source_type, source_config)
    
    async def check_update(self) -> Optional[UpdateInfo]:
        """
        Check for available updates.
        
        Returns
        -------
        Optional[UpdateInfo]
            Update information if available, None otherwise
        """
        try:
            # Get current version
            current_version = self.config.get("app.version")
            if not current_version:
                logger.warning("Current version not configured")
                return None
            
            # Get channel
            channel = self.config.get("update.channel", CHANNEL_STABLE)
            
            # Fetch available versions
            versions = await self.source.get_versions(channel)
            
            if not versions:
                logger.info("No versions available")
                return None
            
            # Find latest version
            latest = self._find_latest_version(versions, current_version)
            
            if not latest:
                logger.info("No updates available")
                return None
            
            # Check if we should skip this version
            if self.skip_version and latest.version == self.skip_version:
                logger.info(f"Skipping version {latest.version}")
                return None
            
            # Check if we're in remind later period
            if self.remind_later_until and datetime.now() < self.remind_later_until:
                logger.info("In remind later period")
                return None
            
            self.last_check = datetime.now()
            return latest
            
        except Exception as e:
            logger.error(f"Update check failed: {e}")
            raise UpdateError(f"Failed to check for updates: {e}")
    
    def _find_latest_version(self, versions: Dict[str, Any], current: str) -> Optional[UpdateInfo]:
        """
        Find the latest available version.
        
        Parameters
        ----------
        versions : dict
            Available versions data
        current : str
            Current version
            
        Returns
        -------
        Optional[UpdateInfo]
            Latest version info if newer than current
        """
        platform = get_platform()
        platform_key = f"{platform}-{'x64' if platform != 'windows' else 'win64'}"
        
        latest_version = None
        latest_info = None
        
        for version, data in versions.items():
            if not is_newer_version(current, version):
                continue
            
            # Check if platform is supported
            platforms = data.get("platforms", {})
            if platform_key not in platforms:
                continue
            
            # Check minimum version requirement
            min_version = data.get("minimum_version")
            if min_version and compare_versions(current, min_version) < 0:
                continue
            
            if not latest_version or is_newer_version(latest_version, version):
                latest_version = version
                platform_data = platforms[platform_key]
                platform_data["version"] = version
                platform_data["notes"] = data.get("notes", "")
                platform_data["pub_date"] = data.get("pub_date", "")
                latest_info = UpdateInfo(platform_data)
        
        return latest_info
    
    async def download_update(self, update_info: UpdateInfo, progress_callback=None) -> Path:
        """
        Download update package with progress tracking.
        
        Parameters
        ----------
        update_info : UpdateInfo
            Update information
        progress_callback : callable, optional
            Progress callback function
            
        Returns
        -------
        Path
            Path to downloaded package
        """
        # Determine if we should use delta
        delta_threshold = self.config.get("update.delta.threshold", 5 * 1024 * 1024)
        use_delta = update_info.should_use_delta(delta_threshold)
        
        if use_delta:
            url = update_info.delta_url
            expected_hash = update_info.delta_hash
            logger.info(f"Using delta update: {url}")
        else:
            url = update_info.url
            expected_hash = update_info.hash
            logger.info(f"Using full update: {url}")
        
        # Download package
        package_path = await self.downloader.download(
            url,
            expected_hash=expected_hash,
            progress_callback=progress_callback
        )
        
        # Verify signature
        if self.config.get("security.verification.strict", True):
            public_key = self.config.get("security.signing.public_key")
            if not self.verifier.verify_package(package_path, update_info.signature, public_key):
                package_path.unlink()
                raise UpdateError("Package signature verification failed")
        
        return package_path
    
    async def apply_update(self, package_path: Path) -> bool:
        """
        Apply update with backup and rollback support.
        
        Parameters
        ----------
        package_path : Path
            Path to update package
            
        Returns
        -------
        bool
            True if successful
        """
        from looma.client.installer import Installer
        
        installer = Installer(self.config)
        
        try:
            # Backup current version
            backup_path = installer.backup_current()
            logger.info(f"Backed up current version to {backup_path}")
            
            # Apply update
            success = await installer.install(package_path)
            
            if not success:
                # Rollback on failure
                logger.error("Installation failed, rolling back")
                installer.rollback(backup_path)
                return False
            
            logger.info("Update installed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply update: {e}")
            raise UpdateError(f"Failed to apply update: {e}")
    
    def schedule_check(self, interval: Optional[int] = None) -> None:
        """
        Schedule periodic update checks.
        
        Parameters
        ----------
        interval : Optional[int]
            Check interval in seconds
        """
        interval = interval or self.config.get("update.check_interval", DEFAULT_CHECK_INTERVAL)
        
        if interval <= 0:
            logger.info("Update checks disabled")
            return
        
        def check_loop():
            while True:
                try:
                    asyncio.run(self._check_and_notify())
                except Exception as e:
                    logger.error(f"Update check error: {e}")
                
                # Sleep until next check
                threading.Event().wait(interval)
        
        self.check_thread = threading.Thread(target=check_loop, daemon=True)
        self.check_thread.start()
        logger.info(f"Scheduled update checks every {interval} seconds")
    
    async def _check_and_notify(self) -> None:
        """Check for updates and notify user if available."""
        update_info = await self.check_update()
        
        if not update_info:
            return
        
        strategy = self.config.get("update.strategy", STRATEGY_PROMPT)
        
        if strategy == STRATEGY_FORCE:
            # Force update
            await self._force_update(update_info)
        elif strategy == STRATEGY_SILENT:
            # Silent download, then prompt
            await self._silent_update(update_info)
        else:
            # Prompt user
            await self._prompt_update(update_info)
    
    async def _prompt_update(self, update_info: UpdateInfo) -> None:
        """
        Prompt user for update.
        
        Parameters
        ----------
        update_info : UpdateInfo
            Update information
        """
        dialog = UpdateDialog(update_info, self.config)
        result = dialog.show()
        
        if result == "update":
            # User chose to update
            package_path = await self.download_update(update_info, dialog.update_progress)
            if await self.apply_update(package_path):
                restart_application()
        elif result == "skip":
            # Skip this version
            self.skip_version = update_info.version
        elif result == "later":
            # Remind later
            remind_interval = self.config.get("update.ui.remind_interval", 86400)
            self.remind_later_until = datetime.now() + timedelta(seconds=remind_interval)
    
    async def _silent_update(self, update_info: UpdateInfo) -> None:
        """
        Silent download, then prompt for installation.
        
        Parameters
        ----------
        update_info : UpdateInfo
            Update information
        """
        # Download in background
        package_path = await self.download_update(update_info)
        
        # Prompt for installation
        dialog = UpdateDialog(update_info, self.config)
        dialog.set_downloaded(package_path)
        result = dialog.show()
        
        if result == "update":
            if await self.apply_update(package_path):
                restart_application()
    
    async def _force_update(self, update_info: UpdateInfo) -> None:
        """
        Force update without prompting.
        
        Parameters
        ----------
        update_info : UpdateInfo
            Update information
        """
        package_path = await self.download_update(update_info)
        if await self.apply_update(package_path):
            restart_application()
    
    def start_background_check(self) -> None:
        """Start background update checking."""
        # Wait a bit before first check
        threading.Timer(1.0, lambda: self.schedule_check()).start()