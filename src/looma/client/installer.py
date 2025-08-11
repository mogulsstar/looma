"""Update installer for Looma client."""

import os
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog

from looma.core.constants import BACKUP_DIR, PLATFORM_LINUX, PLATFORM_MACOS, PLATFORM_WINDOWS
from looma.core.exceptions import UpdateError
from looma.core.utils import ensure_dir, get_executable_path, get_platform

logger = structlog.get_logger()


class Installer:
    """
    Handles update installation with backup and rollback.
    
    Attributes
    ----------
    config : ConfigManager
        Configuration manager
    platform : str
        Current platform
    executable_path : Path
        Path to current executable
    """
    
    def __init__(self, config):
        """
        Initialize installer.
        
        Parameters
        ----------
        config : ConfigManager
            Configuration manager
        """
        self.config = config
        self.platform = get_platform()
        self.executable_path = get_executable_path()
    
    def backup_current(self) -> Path:
        """
        Backup current version.
        
        Returns
        -------
        Path
            Path to backup
            
        Raises
        ------
        UpdateError
            If backup fails
        """
        try:
            # Create backup directory
            backup_base = self.executable_path.parent / BACKUP_DIR
            ensure_dir(backup_base)
            
            # Create timestamped backup directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            version = self.config.get("app.version", "unknown")
            backup_dir = backup_base / f"{version}_{timestamp}"
            ensure_dir(backup_dir)
            
            # Backup executable and related files
            if self.executable_path.is_file():
                # Single file executable
                backup_file = backup_dir / self.executable_path.name
                shutil.copy2(self.executable_path, backup_file)
            else:
                # Directory-based installation
                shutil.copytree(self.executable_path, backup_dir / self.executable_path.name)
            
            logger.info(f"Backed up current version to {backup_dir}")
            return backup_dir
            
        except Exception as e:
            raise UpdateError(f"Failed to backup current version: {e}")
    
    async def install(self, package_path: Path) -> bool:
        """
        Install update package.
        
        Parameters
        ----------
        package_path : Path
            Path to update package
            
        Returns
        -------
        bool
            True if successful
            
        Raises
        ------
        UpdateError
            If installation fails
        """
        try:
            # Extract package based on platform
            extracted_path = await self._extract_package(package_path)
            
            # Platform-specific installation
            if self.platform == PLATFORM_WINDOWS:
                return await self._install_windows(extracted_path)
            elif self.platform == PLATFORM_MACOS:
                return await self._install_macos(extracted_path)
            else:
                return await self._install_linux(extracted_path)
                
        except Exception as e:
            logger.error(f"Installation failed: {e}")
            raise UpdateError(f"Failed to install update: {e}")
    
    async def _extract_package(self, package_path: Path) -> Path:
        """
        Extract update package.
        
        Parameters
        ----------
        package_path : Path
            Package path
            
        Returns
        -------
        Path
            Extracted content path
        """
        # Create temporary extraction directory
        extract_dir = Path(tempfile.mkdtemp(prefix="looma_update_"))
        
        try:
            if package_path.suffix == ".zip":
                # Extract ZIP
                with zipfile.ZipFile(package_path, "r") as zf:
                    zf.extractall(extract_dir)
            elif package_path.suffix in [".tar", ".gz", ".bz2", ".xz"]:
                # Extract TAR archive
                import tarfile
                with tarfile.open(package_path, "r:*") as tf:
                    tf.extractall(extract_dir)
            else:
                # Assume it's a direct executable
                shutil.copy2(package_path, extract_dir / package_path.name)
            
            return extract_dir
            
        except Exception as e:
            shutil.rmtree(extract_dir, ignore_errors=True)
            raise UpdateError(f"Failed to extract package: {e}")
    
    async def _install_windows(self, extracted_path: Path) -> bool:
        """
        Install update on Windows.
        
        Parameters
        ----------
        extracted_path : Path
            Extracted package path
            
        Returns
        -------
        bool
            True if successful
        """
        try:
            # Find new executable
            new_exe = None
            for exe_file in extracted_path.glob("**/*.exe"):
                if exe_file.name == self.executable_path.name:
                    new_exe = exe_file
                    break
            
            if not new_exe:
                # Try to find any exe
                exe_files = list(extracted_path.glob("**/*.exe"))
                if exe_files:
                    new_exe = exe_files[0]
            
            if not new_exe:
                raise UpdateError("No executable found in update package")
            
            # Use batch script for atomic replacement
            batch_script = self._create_windows_update_script(new_exe)
            
            # Execute update script
            subprocess.Popen(
                ["cmd", "/c", str(batch_script)],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Windows installation failed: {e}")
            return False
    
    def _create_windows_update_script(self, new_exe: Path) -> Path:
        """
        Create Windows update batch script.
        
        Parameters
        ----------
        new_exe : Path
            Path to new executable
            
        Returns
        -------
        Path
            Path to batch script
        """
        script_content = f"""
@echo off
echo Updating application...
timeout /t 2 /nobreak > nul
move /y "{self.executable_path}" "{self.executable_path}.old"
move /y "{new_exe}" "{self.executable_path}"
del "{self.executable_path}.old"
start "" "{self.executable_path}"
del "%~f0"
"""
        
        script_path = Path(tempfile.gettempdir()) / "looma_update.bat"
        script_path.write_text(script_content)
        
        return script_path
    
    async def _install_macos(self, extracted_path: Path) -> bool:
        """
        Install update on macOS.
        
        Parameters
        ----------
        extracted_path : Path
            Extracted package path
            
        Returns
        -------
        bool
            True if successful
        """
        try:
            # Find .app bundle or executable
            app_bundle = None
            for app_path in extracted_path.glob("**/*.app"):
                app_bundle = app_path
                break
            
            if app_bundle:
                # Replace entire .app bundle
                target = self.executable_path.parent
                if target.suffix == ".app":
                    # Remove old app
                    shutil.rmtree(target)
                    # Move new app
                    shutil.move(str(app_bundle), str(target))
                else:
                    # Copy to Applications
                    target = Path("/Applications") / app_bundle.name
                    if target.exists():
                        shutil.rmtree(target)
                    shutil.move(str(app_bundle), str(target))
            else:
                # Direct executable replacement
                new_exe = self._find_executable(extracted_path)
                if not new_exe:
                    raise UpdateError("No executable found in update package")
                
                # Make executable
                os.chmod(new_exe, 0o755)
                
                # Replace executable
                shutil.move(str(self.executable_path), f"{self.executable_path}.old")
                shutil.move(str(new_exe), str(self.executable_path))
            
            return True
            
        except Exception as e:
            logger.error(f"macOS installation failed: {e}")
            return False
    
    async def _install_linux(self, extracted_path: Path) -> bool:
        """
        Install update on Linux.
        
        Parameters
        ----------
        extracted_path : Path
            Extracted package path
            
        Returns
        -------
        bool
            True if successful
        """
        try:
            # Find executable or AppImage
            new_exe = None
            
            # Check for AppImage
            for appimage in extracted_path.glob("**/*.AppImage"):
                new_exe = appimage
                break
            
            if not new_exe:
                # Find regular executable
                new_exe = self._find_executable(extracted_path)
            
            if not new_exe:
                raise UpdateError("No executable found in update package")
            
            # Make executable
            os.chmod(new_exe, 0o755)
            
            # Replace executable
            backup_path = f"{self.executable_path}.old"
            shutil.move(str(self.executable_path), backup_path)
            shutil.move(str(new_exe), str(self.executable_path))
            
            # Remove backup
            Path(backup_path).unlink()
            
            return True
            
        except Exception as e:
            logger.error(f"Linux installation failed: {e}")
            return False
    
    def _find_executable(self, path: Path) -> Optional[Path]:
        """
        Find executable in extracted path.
        
        Parameters
        ----------
        path : Path
            Search path
            
        Returns
        -------
        Optional[Path]
            Executable path if found
        """
        # Look for file with same name as current executable
        exe_name = self.executable_path.stem
        
        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.stem == exe_name:
                return file_path
        
        return None
    
    def rollback(self, backup_path: Path) -> bool:
        """
        Rollback to backup version.
        
        Parameters
        ----------
        backup_path : Path
            Path to backup
            
        Returns
        -------
        bool
            True if successful
        """
        try:
            if not backup_path.exists():
                logger.error(f"Backup not found: {backup_path}")
                return False
            
            # Find backup executable
            if self.executable_path.is_file():
                # Single file
                backup_exe = backup_path / self.executable_path.name
                if backup_exe.exists():
                    shutil.copy2(backup_exe, self.executable_path)
                    logger.info("Rolled back to backup version")
                    return True
            else:
                # Directory
                backup_dir = backup_path / self.executable_path.name
                if backup_dir.exists():
                    shutil.rmtree(self.executable_path)
                    shutil.copytree(backup_dir, self.executable_path)
                    logger.info("Rolled back to backup version")
                    return True
            
            logger.error("Failed to rollback: backup executable not found")
            return False
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False