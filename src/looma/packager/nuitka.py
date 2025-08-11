"""Nuitka packaging engine for Looma."""

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List

from looma.core.exceptions import PackagingError
from looma.core.utils import ensure_dir, get_platform, run_command
from looma.packager.base import BasePackager


class NuitkaPackager(BasePackager):
    """
    Nuitka packaging engine implementation.
    
    Nuitka compiles Python to C++ for better performance and smaller size.
    """
    
    def is_installed(self) -> bool:
        """
        Check if Nuitka is installed.
        
        Returns
        -------
        bool
            True if Nuitka is available
        """
        returncode, stdout, stderr = run_command(["nuitka", "--version"])
        return returncode == 0
    
    def prepare(self, app_path: Path, config: Dict[str, Any]) -> None:
        """
        Prepare the application for packaging with Nuitka.
        
        Parameters
        ----------
        app_path : Path
            Path to the application entry point
        config : dict
            Packaging configuration
            
        Raises
        ------
        PackagingError
            If preparation fails
        """
        if not self.is_installed():
            raise PackagingError("Nuitka is not installed. Install with: pip install nuitka")
        
        self.validate_config()
        ensure_dir(self.output_dir)
        ensure_dir(self.build_dir)
    
    def build(self, spec: Dict[str, Any]) -> Path:
        """
        Build the application with Nuitka.
        
        Parameters
        ----------
        spec : dict
            Build specification
            
        Returns
        -------
        Path
            Path to the packaged application
            
        Raises
        ------
        PackagingError
            If build fails
        """
        try:
            # Run pre-build hooks
            self.run_hooks("pre_build")
            
            # Build command
            cmd = self._build_command(spec)
            
            # Execute Nuitka
            returncode, stdout, stderr = run_command(cmd, timeout=600)
            
            if returncode != 0:
                raise PackagingError(f"Nuitka build failed: {stderr}")
            
            # Find the output executable
            output_path = self._find_output(spec)
            
            if not output_path or not output_path.exists():
                raise PackagingError("Build succeeded but output not found")
            
            # Copy data files
            self._copy_data_files(spec, output_path.parent)
            
            # Run post-build hooks
            self.run_hooks("post_build")
            
            return output_path
            
        except Exception as e:
            self.run_hooks("on_error")
            raise PackagingError(f"Build failed: {e}")
    
    def inject_client(self, dist_path: Path) -> None:
        """
        Inject Looma update client into the distribution.
        
        Parameters
        ----------
        dist_path : Path
            Path to the distribution directory
            
        Raises
        ------
        PackagingError
            If injection fails
        """
        try:
            # For Nuitka standalone mode, the client needs to be compiled in
            # or placed alongside the executable
            client_source = Path(__file__).parent.parent / "client"
            
            if dist_path.is_file():
                # Single file output - place client next to executable
                client_dest = dist_path.parent / "looma_client"
            else:
                # Directory output
                client_dest = dist_path / "looma_client"
            
            if not client_source.exists():
                raise PackagingError(f"Client source not found: {client_source}")
            
            # Create destination directory
            ensure_dir(client_dest)
            
            # Copy client files
            shutil.copytree(client_source, client_dest, dirs_exist_ok=True)
            
        except Exception as e:
            raise PackagingError(f"Failed to inject client: {e}")
    
    def _build_command(self, spec: Dict[str, Any]) -> List[str]:
        """
        Build Nuitka command.
        
        Parameters
        ----------
        spec : dict
            Build specification
            
        Returns
        -------
        List[str]
            Command arguments
        """
        cmd = ["nuitka"]
        
        # Standalone mode (includes Python runtime)
        if spec.get("one_file"):
            cmd.append("--onefile")
        else:
            cmd.append("--standalone")
        
        # Follow imports
        cmd.append("--follow-imports")
        
        # Output directory
        cmd.extend(["--output-dir", str(self.build_dir)])
        
        # Console/GUI mode
        if not spec.get("console"):
            cmd.append("--windows-disable-console")
        
        # Icon
        if spec.get("icon"):
            if os.name == "nt":
                cmd.extend(["--windows-icon-from-ico", spec["icon"]])
            elif get_platform() == "macos":
                cmd.extend(["--macos-app-icon", spec["icon"]])
        
        # App name
        cmd.extend(["--product-name", spec["name"]])
        cmd.extend(["--file-version", spec.get("version", "1.0.0")])
        
        # Company info (if available)
        if self.config.get("app", {}).get("author"):
            cmd.extend(["--company-name", self.config["app"]["author"]])
        
        # Hidden imports
        for hidden_import in spec.get("hidden_imports", []):
            cmd.extend(["--include-module", hidden_import])
        
        # Exclude modules
        for exclude in spec.get("exclude_modules", []):
            cmd.extend(["--nofollow-import-to", exclude])
        
        # Include data files
        for src, dst in spec.get("data_files", []):
            cmd.extend(["--include-data-files", f"{src}={dst}"])
        
        # Include directories
        for include_file in spec.get("include_files", []):
            if Path(include_file).is_dir():
                cmd.extend(["--include-data-dir", f"{include_file}={Path(include_file).name}"])
        
        # Optimization
        if spec.get("optimize"):
            cmd.append("--python-flag=-O")
        
        # Enable plugins for common frameworks
        cmd.extend([
            "--enable-plugin=tk-inter",
            "--enable-plugin=numpy",
            "--enable-plugin=multiprocessing",
        ])
        
        # Assume yes to prompts
        cmd.append("--assume-yes-for-downloads")
        
        # Show progress
        cmd.append("--show-progress")
        cmd.append("--show-memory")
        
        # Entry point
        cmd.append(str(self.app_path))
        
        return cmd
    
    def _find_output(self, spec: Dict[str, Any]) -> Path:
        """
        Find the output executable.
        
        Parameters
        ----------
        spec : dict
            Build specification
            
        Returns
        -------
        Path
            Path to output executable
        """
        app_name = spec["name"]
        
        if spec.get("one_file"):
            # Single file output
            if os.name == "nt":
                output = self.build_dir / f"{app_name}.exe"
            else:
                output = self.build_dir / app_name
        else:
            # Standalone directory output
            if os.name == "nt":
                output = self.build_dir / f"{app_name}.dist" / f"{app_name}.exe"
            else:
                output = self.build_dir / f"{app_name}.dist" / app_name
        
        # Move to final output directory
        if output.exists():
            final_output = self.output_dir / output.name
            shutil.move(str(output), str(final_output))
            return final_output
        
        return output
    
    def _copy_data_files(self, spec: Dict[str, Any], output_dir: Path) -> None:
        """
        Copy data files to output directory.
        
        Parameters
        ----------
        spec : dict
            Build specification
        output_dir : Path
            Output directory
        """
        # Copy include files
        for include_file in spec.get("include_files", []):
            src = Path(include_file)
            if src.exists():
                dst = output_dir / src.name
                if src.is_file():
                    shutil.copy2(src, dst)
                else:
                    shutil.copytree(src, dst, dirs_exist_ok=True)