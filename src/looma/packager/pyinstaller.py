"""PyInstaller packaging engine for Looma."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from looma.core.exceptions import PackagingError
from looma.core.utils import ensure_dir, run_command
from looma.packager.base import BasePackager


class PyInstallerPackager(BasePackager):
    """
    PyInstaller packaging engine implementation.

    Attributes
    ----------
    spec_file : Path
        Path to the spec file
    """

    def get_parameters_schema(self) -> Dict[str, Any]:
        """Get PyInstaller-specific parameter schema.

        Returns
        -------
        dict
            PyInstaller parameter schema
        """
        # Get base parameters from parent class
        schema = super().get_parameters_schema()

        # Add PyInstaller-specific parameters
        pyinstaller_params = {
            "onefile": {
                "type": "flag",
                "description": "Create a single executable file",
                "default": False,
                "required": False
            },
            "onedir": {
                "type": "flag",
                "description": "Create a directory with executable and dependencies",
                "default": True,
                "required": False
            },
            "console": {
                "type": "flag",
                "description": "Display console window (disable for GUI apps)",
                "default": True,
                "required": False
            },
            "windowed": {
                "type": "flag",
                "description": "Suppress console window (same as noconsole)",
                "default": False,
                "required": False
            },
            "icon": {
                "type": "input",
                "description": "Path to application icon (.ico for Windows, .icns for macOS)",
                "default": "",
                "required": False
            },
            "name": {
                "type": "input",
                "description": "Name of the output executable",
                "default": "",
                "required": False
            },
            "add_data": {
                "type": "list",
                "description": "Additional data files or directories (format: source:dest)",
                "default": [],
                "required": False
            },
            "add_binary": {
                "type": "list",
                "description": "Additional binary files (format: source:dest)",
                "default": [],
                "required": False
            },
            "paths": {
                "type": "list",
                "description": "Additional paths to search for imports",
                "default": [],
                "required": False
            },
            "clean": {
                "type": "flag",
                "description": "Clean PyInstaller cache before building",
                "default": False,
                "required": False
            },
            "noupx": {
                "type": "flag",
                "description": "Disable UPX compression",
                "default": False,
                "required": False
            },
            "strip": {
                "type": "flag",
                "description": "Strip debug symbols from executable",
                "default": False,
                "required": False
            },
            "debug": {
                "type": "flag",
                "description": "Enable debug output",
                "default": False,
                "required": False
            },
            "log_level": {
                "type": "input",
                "description": "Log level (TRACE, DEBUG, INFO, WARN, ERROR, CRITICAL)",
                "default": "INFO",
                "required": False,
                "choices": ["TRACE", "DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"]
            },
            "version_file": {
                "type": "input",
                "description": "Path to version file for Windows",
                "default": "",
                "required": False
            },
            "manifest": {
                "type": "input",
                "description": "Path to Windows manifest file",
                "default": "",
                "required": False
            },
            "runtime_hooks": {
                "type": "list",
                "description": "Runtime hook scripts to execute",
                "default": [],
                "required": False
            },
            "collect_all": {
                "type": "list",
                "description": "Packages to collect all submodules, data files, and binaries",
                "default": [],
                "required": False
            },
            "collect_data": {
                "type": "list",
                "description": "Packages to collect data files from",
                "default": [],
                "required": False
            },
            "collect_binaries": {
                "type": "list",
                "description": "Packages to collect binary files from",
                "default": [],
                "required": False
            },
            "collect_submodules": {
                "type": "list",
                "description": "Packages to collect all submodules from",
                "default": [],
                "required": False
            },
            "copy_metadata": {
                "type": "list",
                "description": "Packages to copy metadata from",
                "default": [],
                "required": False
            },
            "recursive_copy_metadata": {
                "type": "list",
                "description": "Packages to recursively copy metadata from",
                "default": [],
                "required": False
            }
        }

        # Merge with base parameters
        schema.update(pyinstaller_params)
        return schema

    def get_schema_file(self) -> Optional[Path]:
        """Deprecated: Use get_parameters_schema() instead."""
        return None

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize PyInstaller packager.

        Parameters
        ----------
        config : dict
            Packaging configuration
        """
        super().__init__(config)
        self.spec_file = None

    def is_installed(self) -> bool:
        """
        Check if PyInstaller is installed.

        Returns
        -------
        bool
            True if PyInstaller is available
        """
        try:
            import PyInstaller
            return True
        except ImportError:
            return False

    def prepare(self, app_path: Path, config: Dict[str, Any]) -> None:
        """
        Prepare the application for packaging with PyInstaller.

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
            raise PackagingError("PyInstaller is not installed. Install with: pip install pyinstaller")

        self.validate_config()
        ensure_dir(self.output_dir)
        ensure_dir(self.build_dir)

        # Generate spec file
        self.spec_file = self._generate_spec_file(app_path, config)

    def build(self, spec: Dict[str, Any]) -> Path:
        """
        Build the application with PyInstaller.

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

            # Execute PyInstaller
            returncode, stdout, stderr = run_command(cmd)

            if returncode != 0:
                raise PackagingError(f"PyInstaller build failed: {stderr}")

            # Find the output executable
            output_path = self._find_output(spec)

            if not output_path or not output_path.exists():
                raise PackagingError("Build succeeded but output not found")

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
            # Copy Looma client module
            client_source = Path(__file__).parent.parent / "client"
            client_dest = dist_path / "_internal" / "looma_client"

            if not client_source.exists():
                raise PackagingError(f"Client source not found: {client_source}")

            # Create destination directory
            ensure_dir(client_dest)

            # Copy client files
            shutil.copytree(client_source, client_dest, dirs_exist_ok=True)

            # Create bootstrap script
            bootstrap_script = dist_path / "_internal" / "looma_bootstrap.py"
            bootstrap_content = self._generate_bootstrap_script()
            bootstrap_script.write_text(bootstrap_content)

        except Exception as e:
            raise PackagingError(f"Failed to inject client: {e}")

    def _generate_spec_file(self, app_path: Path, config: Dict[str, Any]) -> Path:
        """
        Generate PyInstaller spec file.

        Parameters
        ----------
        app_path : Path
            Application entry point
        config : dict
            Configuration

        Returns
        -------
        Path
            Path to generated spec file
        """
        spec = self.create_spec()
        app_name = spec["name"]

        spec_content = f"""
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{app_path}'],
    pathex=[],
    binaries=[],
    datas={self._format_data_files(spec["data_files"])},
    hiddenimports={spec["hidden_imports"]},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes={spec["exclude_modules"]},
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

"""

        if spec["one_file"]:
            spec_content += f"""
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{app_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console={spec["console"]},
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon={repr(spec.get("icon"))},
)
"""
        else:
            spec_content += f"""
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{app_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console={spec["console"]},
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon={repr(spec.get("icon"))},
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='{app_name}',
)
"""

        spec_file = Path(f"{app_name}.spec")
        spec_file.write_text(spec_content)

        return spec_file

    def _format_data_files(self, data_files: List[tuple]) -> str:
        """
        Format data files for spec file.

        Parameters
        ----------
        data_files : List[tuple]
            Data files as (source, destination) tuples

        Returns
        -------
        str
            Formatted data files string
        """
        if not data_files:
            return "[]"

        formatted = []
        for src, dst in data_files:
            formatted.append(f"('{src}', '{dst}')")

        return "[" + ", ".join(formatted) + "]"

    def _build_command(self, spec: Dict[str, Any]) -> List[str]:
        """
        Build PyInstaller command.

        Parameters
        ----------
        spec : dict
            Build specification

        Returns
        -------
        List[str]
            Command arguments
        """
        cmd = ["pyinstaller"]

        # Clean build
        if self.config.get("build", {}).get("clean", True):
            cmd.append("--clean")

        # Output directory
        cmd.extend(["--distpath", str(self.output_dir)])
        cmd.extend(["--workpath", str(self.build_dir)])

        # Optimization level
        if spec.get("optimize"):
            cmd.extend(["-O", str(spec["optimize"])])

        # No confirm
        cmd.append("-y")

        # Spec file
        cmd.append(str(self.spec_file))

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

        if spec["one_file"]:
            # Single file output
            if os.name == "nt":
                output = self.output_dir / f"{app_name}.exe"
            else:
                output = self.output_dir / app_name
        else:
            # Directory output
            if os.name == "nt":
                output = self.output_dir / app_name / f"{app_name}.exe"
            else:
                output = self.output_dir / app_name / app_name

        return output

    def _generate_bootstrap_script(self) -> str:
        """
        Generate bootstrap script for update client.

        Returns
        -------
        str
            Bootstrap script content
        """
        return """
# Looma Update Client Bootstrap
import sys
import os
from pathlib import Path

# Add client to path
client_path = Path(__file__).parent / "looma_client"
sys.path.insert(0, str(client_path))

# Import and initialize update client
try:
    from looma.client import UpdateClient

    # Start update check in background
    client = UpdateClient()
    client.start_background_check()
except ImportError:
    # Client not available, continue without updates
    pass
"""