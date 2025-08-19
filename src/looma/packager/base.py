"""Base packager interface for Looma."""

from abc import abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from looma.core.exceptions import PackagingError
from looma.core.plugin_base import PluginInterface


class BasePackager(PluginInterface):
    """
    Abstract base class for packaging engines.
    
    Attributes
    ----------
    config : dict
        Packaging configuration
    app_path : Path
        Path to the application
    output_dir : Path
        Output directory for packaged application
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the packager.
        
        Parameters
        ----------
        config : dict
            Packaging configuration
        """
        self.config = config
        self.app_path = Path(config.get("packaging", {}).get("entry_point", "main.py"))
        self.output_dir = Path(config.get("build", {}).get("output_dir", "dist"))
        self.build_dir = Path(config.get("build", {}).get("build_dir", "build"))
    
    @abstractmethod
    def prepare(self, app_path: Path, config: Dict[str, Any]) -> None:
        """
        Prepare the application for packaging.
        
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
        pass
    
    @abstractmethod
    def build(self, spec: Dict[str, Any]) -> Path:
        """
        Build the application package.
        
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
        pass
    
    @abstractmethod
    def inject_client(self, dist_path: Path) -> None:
        """
        Inject update client into distribution.
        
        Parameters
        ----------
        dist_path : Path
            Path to the distribution directory
            
        Raises
        ------
        PackagingError
            If injection fails
        """
        pass
    
    def clean(self) -> None:
        """
        Clean build artifacts.
        
        Raises
        ------
        PackagingError
            If cleaning fails
        """
        import shutil
        
        try:
            if self.build_dir.exists():
                shutil.rmtree(self.build_dir)
            
            # Clean PyInstaller-specific directories
            for dir_name in ["__pycache__", ".pytest_cache", "*.egg-info"]:
                for path in Path(".").glob(f"**/{dir_name}"):
                    if path.is_dir():
                        shutil.rmtree(path)
            
            # Clean spec files
            for spec_file in Path(".").glob("*.spec"):
                spec_file.unlink()
        except Exception as e:
            raise PackagingError(f"Failed to clean build artifacts: {e}")
    
    def get_platform_options(self, platform: str) -> Dict[str, Any]:
        """
        Get platform-specific packaging options.
        
        Parameters
        ----------
        platform : str
            Platform name (windows, macos, linux)
            
        Returns
        -------
        dict
            Platform-specific options
        """
        return self.config.get("platforms", {}).get(platform, {})
    
    def run_hooks(self, hook_type: str) -> None:
        """
        Run build hooks.
        
        Parameters
        ----------
        hook_type : str
            Hook type (pre_build, post_build, on_error)
            
        Raises
        ------
        PackagingError
            If hook execution fails
        """
        import subprocess
        
        hooks = self.config.get("build", {}).get("hooks", {}).get(hook_type, [])
        
        for hook in hooks:
            try:
                subprocess.run(hook, shell=True, check=True)
            except subprocess.CalledProcessError as e:
                raise PackagingError(f"Hook '{hook}' failed: {e}")
    
    def validate_config(self) -> bool:
        """
        Validate packaging configuration.
        
        Returns
        -------
        bool
            True if configuration is valid
            
        Raises
        ------
        PackagingError
            If configuration is invalid
        """
        packaging_config = self.config.get("packaging", {})
        
        if not packaging_config.get("entry_point"):
            raise PackagingError("Entry point not specified in configuration")
        
        entry_point = Path(packaging_config["entry_point"])
        if not entry_point.exists():
            raise PackagingError(f"Entry point not found: {entry_point}")
        
        return True
    
    def get_hidden_imports(self) -> List[str]:
        """
        Get list of hidden imports.
        
        Returns
        -------
        List[str]
            Hidden imports
        """
        return self.config.get("packaging", {}).get("hidden_imports", [])
    
    def get_exclude_modules(self) -> List[str]:
        """
        Get list of modules to exclude.
        
        Returns
        -------
        List[str]
            Modules to exclude
        """
        return self.config.get("packaging", {}).get("exclude_modules", [])
    
    def get_include_files(self) -> List[str]:
        """
        Get list of files to include.
        
        Returns
        -------
        List[str]
            Files to include
        """
        return self.config.get("packaging", {}).get("include_files", [])
    
    def get_data_files(self) -> List[tuple]:
        """
        Get list of data files.
        
        Returns
        -------
        List[tuple]
            Data files as (source, destination) tuples
        """
        data_files = []
        for item in self.config.get("packaging", {}).get("data_files", []):
            if ":" in item:
                src, dst = item.split(":", 1)
                data_files.append((src, dst))
            else:
                data_files.append((item, "."))
        return data_files
    
    def create_spec(self) -> Dict[str, Any]:
        """
        Create build specification.
        
        Returns
        -------
        dict
            Build specification
        """
        packaging_config = self.config.get("packaging", {})
        app_config = self.config.get("app", {})
        
        spec = {
            "name": app_config.get("name", "app"),
            "version": app_config.get("version", "1.0.0"),
            "entry_point": packaging_config.get("entry_point"),
            "one_file": packaging_config.get("one_file", False),
            "console": packaging_config.get("console", True),
            "icon": packaging_config.get("icon"),
            "hidden_imports": self.get_hidden_imports(),
            "exclude_modules": self.get_exclude_modules(),
            "include_files": self.get_include_files(),
            "data_files": self.get_data_files(),
            "optimize": packaging_config.get("optimize", 0),
        }
        
        return spec
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        """
        Get parameter schema for this packager.
        
        Returns a dictionary describing available parameters, their types,
        descriptions, and default values. This replaces external JSON schema files.
        
        Returns
        -------
        dict
            Parameter schema with structure:
            {
                "parameter_name": {
                    "type": "flag" | "input" | "list",
                    "description": "Parameter description",
                    "default": default_value,
                    "required": bool,
                    "choices": [list of valid choices] (optional)
                }
            }
        """
        # Base parameters common to all packagers
        return {
            "entry_point": {
                "type": "input",
                "description": "Main Python file to package",
                "default": "main.py",
                "required": True
            },
            "output_dir": {
                "type": "input",
                "description": "Directory for output files",
                "default": "dist",
                "required": False
            },
            "hidden_imports": {
                "type": "list",
                "description": "Additional modules to include (one per line)",
                "default": [],
                "required": False
            },
            "exclude_modules": {
                "type": "list",
                "description": "Modules to exclude from package (one per line)",
                "default": [],
                "required": False
            },
            "data_files": {
                "type": "list",
                "description": "Additional data files to include (one per line, format: source:dest)",
                "default": [],
                "required": False
            }
        }