"""cx_Freeze packaging engine for Looma."""

import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

from looma.core.exceptions import PackagingError
from looma.core.utils import ensure_dir, run_command
from looma.packager.base import BasePackager


class CxFreezePackager(BasePackager):
    """
    cx_Freeze packaging engine implementation.

    cx_Freeze is a cross-platform packaging tool that creates standalone executables.
    """

    def get_parameters_schema(self) -> Dict[str, Any]:
        """Get cx_Freeze-specific parameter schema.

        Returns
        -------
        dict
            cx_Freeze parameter schema
        """
        # Get base parameters from parent class
        schema = super().get_parameters_schema()

        # Add cx_Freeze-specific parameters
        cxfreeze_params = {
            "target_name": {
                "type": "input",
                "description": "Name of the target executable",
                "default": "",
                "required": False
            },
            "target_dir": {
                "type": "input",
                "description": "Directory to build the target in",
                "default": "build",
                "required": False
            },
            "icon": {
                "type": "input",
                "description": "Path to application icon",
                "default": "",
                "required": False
            },
            "base": {
                "type": "input",
                "description": "Base executable (Win32GUI for Windows GUI apps)",
                "default": "",
                "required": False,
                "choices": ["", "Console", "Win32GUI"]
            },
            "init_script": {
                "type": "input",
                "description": "Path to initialization script",
                "default": "",
                "required": False
            },
            "compress": {
                "type": "flag",
                "description": "Compress the library archive",
                "default": True,
                "required": False
            },
            "copy_dependent_files": {
                "type": "flag",
                "description": "Copy dependent files to the target directory",
                "default": True,
                "required": False
            },
            "create_shared_zip": {
                "type": "flag",
                "description": "Create a shared zip file for all executables",
                "default": True,
                "required": False
            },
            "append_script_to_exe": {
                "type": "flag",
                "description": "Append the script to the executable",
                "default": True,
                "required": False
            },
            "include_in_shared_zip": {
                "type": "flag",
                "description": "Include modules in shared zip file",
                "default": True,
                "required": False
            },
            "optimize": {
                "type": "input",
                "description": "Optimization level (0, 1, or 2)",
                "default": "0",
                "required": False,
                "choices": ["0", "1", "2"]
            },
            "packages": {
                "type": "list",
                "description": "Packages to include (one per line)",
                "default": [],
                "required": False
            },
            "excludes": {
                "type": "list",
                "description": "Modules to exclude (one per line)",
                "default": [],
                "required": False
            },
            "includes": {
                "type": "list",
                "description": "Modules to include (one per line)",
                "default": [],
                "required": False
            },
            "bin_includes": {
                "type": "list",
                "description": "Binary files to include (one per line)",
                "default": [],
                "required": False
            },
            "bin_excludes": {
                "type": "list",
                "description": "Binary files to exclude (one per line)",
                "default": [],
                "required": False
            },
            "bin_path_includes": {
                "type": "list",
                "description": "Binary paths to include (one per line)",
                "default": [],
                "required": False
            },
            "bin_path_excludes": {
                "type": "list",
                "description": "Binary paths to exclude (one per line)",
                "default": [],
                "required": False
            },
            "include_files": {
                "type": "list",
                "description": "Files to include (format: source:dest or just source)",
                "default": [],
                "required": False
            },
            "zip_includes": {
                "type": "list",
                "description": "Files to include in the zip file (format: source:dest)",
                "default": [],
                "required": False
            },
            "zip_excludes": {
                "type": "list",
                "description": "Patterns to exclude from the zip file",
                "default": [],
                "required": False
            },
            "silent": {
                "type": "flag",
                "description": "Suppress output during build",
                "default": False,
                "required": False
            },
            "namespace_packages": {
                "type": "list",
                "description": "Namespace packages to include (one per line)",
                "default": [],
                "required": False
            },
            "replace_paths": {
                "type": "list",
                "description": "Paths to replace (format: old=new)",
                "default": [],
                "required": False
            },
            "constants": {
                "type": "list",
                "description": "Constants to set (format: name=value)",
                "default": [],
                "required": False
            },
            "include_msvcr": {
                "type": "flag",
                "description": "Include Microsoft Visual C runtime",
                "default": False,
                "required": False
            }
        }

        # Merge with base parameters
        schema.update(cxfreeze_params)
        return schema

    def is_installed(self) -> bool:
        """
        Check if cx_Freeze is installed.

        Returns
        -------
        bool
            True if cx_Freeze is available
        """
        try:
            import cx_Freeze
            return True
        except ImportError:
            return False

    def prepare(self, app_path: Path, config: Dict[str, Any]) -> None:
        """
        Prepare the application for packaging with cx_Freeze.

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
            raise PackagingError("cx_Freeze is not installed. Install with: pip install cx-freeze")

        self.validate_config()
        ensure_dir(self.output_dir)
        ensure_dir(self.build_dir)

        # Generate setup script
        self.setup_script = self._generate_setup_script(app_path, config)

    def build(self, spec: Dict[str, Any]) -> Path:
        """
        Build the application with cx_Freeze.

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

            # Execute cx_Freeze
            returncode, stdout, stderr = run_command(cmd)

            if returncode != 0:
                raise PackagingError(f"cx_Freeze build failed: {stderr}")

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
        finally:
            # Clean up setup script
            if hasattr(self, 'setup_script') and self.setup_script.exists():
                self.setup_script.unlink()

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

            if dist_path.is_file():
                # Single file not directly supported by cx_Freeze
                # Place client in the same directory
                client_dest = dist_path.parent / "looma_client"
            else:
                # Directory output - place in lib subdirectory
                client_dest = dist_path / "lib" / "looma_client"

            if not client_source.exists():
                raise PackagingError(f"Client source not found: {client_source}")

            # Create destination directory
            ensure_dir(client_dest)

            # Copy client files
            shutil.copytree(client_source, client_dest, dirs_exist_ok=True)

            # Add initialization hook
            if dist_path.is_dir():
                init_file = dist_path / "__looma_init__.py"
                init_content = self._generate_init_script()
                init_file.write_text(init_content)

        except Exception as e:
            raise PackagingError(f"Failed to inject client: {e}")

    def _generate_setup_script(self, app_path: Path, config: Dict[str, Any]) -> Path:
        """
        Generate cx_Freeze setup script.

        Parameters
        ----------
        app_path : Path
            Application entry point
        config : dict
            Configuration

        Returns
        -------
        Path
            Path to generated setup script
        """
        spec = self.create_spec()

        setup_content = f"""
import sys
from cx_Freeze import setup, Executable

# Dependencies
build_exe_options = {{
    "packages": {spec.get("hidden_imports", [])},
    "excludes": {spec.get("exclude_modules", [])},
    "include_files": {self._format_include_files(spec)},
    "optimize": {spec.get("optimize", 0)},
}}

# Platform-specific options
base = None
icon = {repr(spec.get("icon"))}

if sys.platform == "win32":
    if not {spec.get("console", True)}:
        base = "Win32GUI"

executables = [
    Executable(
        "{app_path}",
        base=base,
        icon=icon,
        target_name="{spec['name']}",
    )
]

setup(
    name="{spec['name']}",
    version="{spec.get('version', '1.0.0')}",
    description="{self.config.get('app', {}).get('description', '')}",
    options={{"build_exe": build_exe_options}},
    executables=executables,
)
"""

        setup_file = Path("cx_freeze_setup.py")
        setup_file.write_text(setup_content)

        return setup_file

    def _format_include_files(self, spec: Dict[str, Any]) -> str:
        """
        Format include files for cx_Freeze.

        Parameters
        ----------
        spec : dict
            Build specification

        Returns
        -------
        str
            Formatted include files list
        """
        include_files = []

        # Add data files
        for src, dst in spec.get("data_files", []):
            include_files.append(f"('{src}', '{dst}')")

        # Add include files
        for include_file in spec.get("include_files", []):
            include_files.append(f"'{include_file}'")

        return "[" + ", ".join(include_files) + "]"

    def _build_command(self, spec: Dict[str, Any]) -> List[str]:
        """
        Build cx_Freeze command.

        Parameters
        ----------
        spec : dict
            Build specification

        Returns
        -------
        List[str]
            Command arguments
        """
        cmd = [sys.executable, str(self.setup_script), "build_exe"]

        # Output directory
        cmd.extend(["--build-exe", str(self.output_dir)])

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

        # cx_Freeze creates a directory with the executable inside
        if os.name == "nt":
            output = self.output_dir / f"{app_name}.exe"
        else:
            output = self.output_dir / app_name

        return output

    def _generate_init_script(self) -> str:
        """
        Generate initialization script for update client.

        Returns
        -------
        str
            Initialization script content
        """
        return """
# Looma Update Client Initialization
import sys
from pathlib import Path

# Add client to path
lib_path = Path(__file__).parent / "lib"
if lib_path.exists():
    sys.path.insert(0, str(lib_path))

# Try to import and initialize update client
try:
    from looma_client import UpdateClient

    # Start update check in background
    client = UpdateClient()
    client.start_background_check()
except ImportError:
    # Client not available, continue without updates
    pass
"""
