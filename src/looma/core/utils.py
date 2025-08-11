"""Utility functions for Looma."""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from packaging import version

from looma.core.constants import (
    PLATFORM_LINUX,
    PLATFORM_MACOS,
    PLATFORM_WINDOWS,
)


def get_platform() -> str:
    """
    Get the current platform.
    
    Returns
    -------
    str
        Platform identifier (windows, macos, or linux)
    """
    system = platform.system().lower()
    if system == "windows":
        return PLATFORM_WINDOWS
    elif system == "darwin":
        return PLATFORM_MACOS
    elif system == "linux":
        return PLATFORM_LINUX
    else:
        return PLATFORM_LINUX  # Default to Linux for unknown systems


def get_platform_info() -> Dict[str, str]:
    """
    Get detailed platform information.
    
    Returns
    -------
    dict
        Platform details including OS, version, architecture, etc.
    """
    return {
        "platform": get_platform(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
    }


def ensure_dir(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Parameters
    ----------
    path : Union[str, Path]
        Directory path
        
    Returns
    -------
    Path
        The directory path as a Path object
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_delete(path: Union[str, Path]) -> bool:
    """
    Safely delete a file or directory.
    
    Parameters
    ----------
    path : Union[str, Path]
        Path to delete
        
    Returns
    -------
    bool
        True if successful, False otherwise
    """
    try:
        path = Path(path)
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        return True
    except Exception:
        return False


def calculate_hash(file_path: Union[str, Path], algorithm: str = "sha256") -> str:
    """
    Calculate the hash of a file.
    
    Parameters
    ----------
    file_path : Union[str, Path]
        Path to the file
    algorithm : str, optional
        Hash algorithm (default: sha256)
        
    Returns
    -------
    str
        Hexadecimal hash digest
    """
    file_path = Path(file_path)
    hasher = hashlib.new(algorithm)
    
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    
    return hasher.hexdigest()


def verify_hash(file_path: Union[str, Path], expected_hash: str, algorithm: str = "sha256") -> bool:
    """
    Verify a file's hash.
    
    Parameters
    ----------
    file_path : Union[str, Path]
        Path to the file
    expected_hash : str
        Expected hash value
    algorithm : str, optional
        Hash algorithm (default: sha256)
        
    Returns
    -------
    bool
        True if hash matches, False otherwise
    """
    actual_hash = calculate_hash(file_path, algorithm)
    return actual_hash.lower() == expected_hash.lower()


def load_json(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load JSON from a file.
    
    Parameters
    ----------
    file_path : Union[str, Path]
        Path to JSON file
        
    Returns
    -------
    dict
        Parsed JSON data
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Dict[str, Any], file_path: Union[str, Path], indent: int = 2) -> None:
    """
    Save data to a JSON file.
    
    Parameters
    ----------
    data : dict
        Data to save
    file_path : Union[str, Path]
        Path to save file
    indent : int, optional
        JSON indentation (default: 2)
    """
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def load_yaml(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load YAML from a file.
    
    Parameters
    ----------
    file_path : Union[str, Path]
        Path to YAML file
        
    Returns
    -------
    dict
        Parsed YAML data
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(data: Dict[str, Any], file_path: Union[str, Path]) -> None:
    """
    Save data to a YAML file.
    
    Parameters
    ----------
    data : dict
        Data to save
    file_path : Union[str, Path]
        Path to save file
    """
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two version strings.
    
    Parameters
    ----------
    v1 : str
        First version
    v2 : str
        Second version
        
    Returns
    -------
    int
        -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
    """
    ver1 = version.parse(v1)
    ver2 = version.parse(v2)
    
    if ver1 < ver2:
        return -1
    elif ver1 > ver2:
        return 1
    else:
        return 0


def is_newer_version(current: str, available: str) -> bool:
    """
    Check if an available version is newer than the current version.
    
    Parameters
    ----------
    current : str
        Current version
    available : str
        Available version
        
    Returns
    -------
    bool
        True if available version is newer
    """
    return compare_versions(current, available) < 0


def run_command(cmd: List[str], cwd: Optional[Path] = None, timeout: Optional[int] = None) -> tuple:
    """
    Run a command and return output.
    
    Parameters
    ----------
    cmd : List[str]
        Command and arguments
    cwd : Optional[Path]
        Working directory
    timeout : Optional[int]
        Command timeout in seconds
        
    Returns
    -------
    tuple
        (return_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def get_temp_dir() -> Path:
    """
    Get a temporary directory for Looma.
    
    Returns
    -------
    Path
        Temporary directory path
    """
    temp_dir = Path(tempfile.gettempdir()) / "looma"
    ensure_dir(temp_dir)
    return temp_dir


def copy_file(src: Union[str, Path], dst: Union[str, Path]) -> None:
    """
    Copy a file, preserving metadata.
    
    Parameters
    ----------
    src : Union[str, Path]
        Source file path
    dst : Union[str, Path]
        Destination file path
    """
    shutil.copy2(src, dst)


def move_file(src: Union[str, Path], dst: Union[str, Path]) -> None:
    """
    Move a file.
    
    Parameters
    ----------
    src : Union[str, Path]
        Source file path
    dst : Union[str, Path]
        Destination file path
    """
    shutil.move(str(src), str(dst))


def get_file_size(file_path: Union[str, Path]) -> int:
    """
    Get file size in bytes.
    
    Parameters
    ----------
    file_path : Union[str, Path]
        File path
        
    Returns
    -------
    int
        File size in bytes
    """
    return Path(file_path).stat().st_size


def format_size(size_bytes: int) -> str:
    """
    Format file size for human reading.
    
    Parameters
    ----------
    size_bytes : int
        Size in bytes
        
    Returns
    -------
    str
        Formatted size string
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def is_admin() -> bool:
    """
    Check if running with administrator/root privileges.
    
    Returns
    -------
    bool
        True if running as admin/root
    """
    if get_platform() == PLATFORM_WINDOWS:
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        return os.geteuid() == 0


def get_executable_path() -> Path:
    """
    Get the path to the current executable.
    
    Returns
    -------
    Path
        Executable path
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return Path(sys.executable)
    else:
        # Running as script
        return Path(sys.argv[0]).resolve()


def restart_application() -> None:
    """Restart the current application."""
    python = sys.executable
    os.execl(python, python, *sys.argv)