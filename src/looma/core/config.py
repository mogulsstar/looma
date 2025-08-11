"""Configuration management for Looma."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import jsonschema
from dotenv import load_dotenv

from looma.core.constants import CONFIG_FILE, ENV_PREFIX
from looma.core.exceptions import ConfigurationError, ValidationError
from looma.core.utils import load_yaml, save_yaml


class ConfigManager:
    """
    Manages Looma configuration with validation and environment variable support.
    
    Attributes
    ----------
    config_path : Path
        Path to the configuration file
    config : dict
        Loaded configuration dictionary
    schema : dict
        JSON schema for validation
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the configuration manager.
        
        Parameters
        ----------
        config_path : Optional[Path]
            Path to configuration file
        """
        self.config_path = config_path or Path(CONFIG_FILE)
        self.config = {}
        self.schema = self._load_schema()
        
        # Load environment variables
        load_dotenv()
    
    def _load_schema(self) -> Dict[str, Any]:
        """
        Load the configuration schema.
        
        Returns
        -------
        dict
            JSON schema for configuration validation
        """
        return {
            "type": "object",
            "required": ["version", "app"],
            "properties": {
                "version": {"type": "string"},
                "app": {
                    "type": "object",
                    "required": ["name", "version"],
                    "properties": {
                        "name": {"type": "string"},
                        "version": {"type": "string"},
                        "description": {"type": "string"},
                        "author": {"type": "string"},
                        "email": {"type": "string"},
                        "license": {"type": "string"},
                        "url": {"type": "string"},
                        "copyright": {"type": "string"},
                    }
                },
                "packaging": {
                    "type": "object",
                    "required": ["engine", "entry_point"],
                    "properties": {
                        "engine": {"type": "string", "enum": ["pyinstaller", "nuitka", "cxfreeze"]},
                        "entry_point": {"type": "string"},
                        "one_file": {"type": "boolean"},
                        "console": {"type": "boolean"},
                        "icon": {"type": "string"},
                        "include_files": {"type": "array", "items": {"type": "string"}},
                        "data_files": {"type": "array", "items": {"type": "string"}},
                        "hidden_imports": {"type": "array", "items": {"type": "string"}},
                        "exclude_modules": {"type": "array", "items": {"type": "string"}},
                        "optimize": {"type": "integer", "minimum": 0, "maximum": 2},
                    }
                },
                "update": {
                    "type": "object",
                    "required": ["source"],
                    "properties": {
                        "source": {
                            "type": "object",
                            "required": ["type"],
                            "properties": {
                                "type": {"type": "string", "enum": ["github", "gitlab", "s3", "artifactory", "http"]},
                                "repo": {"type": "string"},
                                "token": {"type": "string"},
                                "base_url": {"type": "string"},
                            }
                        },
                        "channel": {"type": "string"},
                        "check_interval": {"type": "integer", "minimum": 0},
                        "strategy": {"type": "string", "enum": ["prompt", "silent", "force"]},
                        "delta": {
                            "type": "object",
                            "properties": {
                                "enabled": {"type": "boolean"},
                                "threshold": {"type": "integer", "minimum": 0},
                                "algorithm": {"type": "string"},
                            }
                        },
                        "ui": {
                            "type": "object",
                            "properties": {
                                "show_release_notes": {"type": "boolean"},
                                "show_progress": {"type": "boolean"},
                                "allow_skip": {"type": "boolean"},
                                "allow_remind_later": {"type": "boolean"},
                                "remind_interval": {"type": "integer", "minimum": 0},
                                "force_after_days": {"type": "integer", "minimum": 0},
                            }
                        }
                    }
                },
                "security": {
                    "type": "object",
                    "properties": {
                        "signing": {
                            "type": "object",
                            "properties": {
                                "enabled": {"type": "boolean"},
                                "private_key_path": {"type": "string"},
                                "public_key": {"type": "string"},
                                "algorithm": {"type": "string"},
                            }
                        },
                        "verification": {
                            "type": "object",
                            "properties": {
                                "strict": {"type": "boolean"},
                                "trusted_keys": {"type": "array", "items": {"type": "string"}},
                                "allow_self_signed": {"type": "boolean"},
                            }
                        },
                        "ssl": {
                            "type": "object",
                            "properties": {
                                "verify": {"type": "boolean"},
                                "ca_bundle": {"type": ["string", "null"]},
                                "client_cert": {"type": ["string", "null"]},
                                "client_key": {"type": ["string", "null"]},
                            }
                        }
                    }
                },
                "platforms": {
                    "type": "object",
                    "properties": {
                        "windows": {"type": "object"},
                        "macos": {"type": "object"},
                        "linux": {"type": "object"},
                    }
                },
                "build": {
                    "type": "object",
                    "properties": {
                        "output_dir": {"type": "string"},
                        "build_dir": {"type": "string"},
                        "clean": {"type": "boolean"},
                        "parallel": {"type": "boolean"},
                        "jobs": {"type": "integer", "minimum": 1},
                        "compression": {
                            "type": "object",
                            "properties": {
                                "enabled": {"type": "boolean"},
                                "algorithm": {"type": "string"},
                                "level": {"type": "integer", "minimum": 1, "maximum": 9},
                            }
                        },
                        "hooks": {
                            "type": "object",
                            "properties": {
                                "pre_build": {"type": "array", "items": {"type": "string"}},
                                "post_build": {"type": "array", "items": {"type": "string"}},
                                "on_error": {"type": "array", "items": {"type": "string"}},
                            }
                        }
                    }
                },
                "logging": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
                        "file": {"type": "string"},
                        "console": {"type": "boolean"},
                        "format": {"type": "string"},
                        "date_format": {"type": "string"},
                        "rotation": {
                            "type": "object",
                            "properties": {
                                "enabled": {"type": "boolean"},
                                "max_size": {"type": "integer", "minimum": 0},
                                "backup_count": {"type": "integer", "minimum": 0},
                                "interval": {"type": "string"},
                            }
                        }
                    }
                },
                "advanced": {
                    "type": "object",
                    "properties": {
                        "proxy": {
                            "type": "object",
                            "properties": {
                                "http": {"type": "string"},
                                "https": {"type": "string"},
                                "no_proxy": {"type": "string"},
                            }
                        },
                        "timeouts": {
                            "type": "object",
                            "properties": {
                                "connection": {"type": "integer", "minimum": 0},
                                "read": {"type": "integer", "minimum": 0},
                                "download": {"type": "integer", "minimum": 0},
                            }
                        },
                        "retry": {
                            "type": "object",
                            "properties": {
                                "max_attempts": {"type": "integer", "minimum": 0},
                                "delay": {"type": "integer", "minimum": 0},
                                "backoff": {"type": "number", "minimum": 1},
                                "max_delay": {"type": "integer", "minimum": 0},
                            }
                        },
                        "cache": {
                            "type": "object",
                            "properties": {
                                "enabled": {"type": "boolean"},
                                "directory": {"type": "string"},
                                "ttl": {"type": "integer", "minimum": 0},
                                "max_size": {"type": "integer", "minimum": 0},
                            }
                        }
                    }
                }
            }
        }
    
    def load(self, path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Load configuration from file or defaults.
        
        Parameters
        ----------
        path : Optional[Path]
            Path to configuration file
            
        Returns
        -------
        dict
            Loaded configuration
            
        Raises
        ------
        ConfigurationError
            If configuration file cannot be loaded
        """
        config_path = path or self.config_path
        
        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path}")
        
        try:
            self.config = load_yaml(config_path)
            self.config = self.merge_env_vars(self.config)
            
            if not self.validate(self.config):
                raise ValidationError("Configuration validation failed")
            
            return self.config
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")
    
    def validate(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration against schema.
        
        Parameters
        ----------
        config : dict
            Configuration to validate
            
        Returns
        -------
        bool
            True if valid, False otherwise
        """
        try:
            jsonschema.validate(config, self.schema)
            return True
        except jsonschema.ValidationError:
            return False
    
    def merge_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge environment variables into configuration.
        
        Parameters
        ----------
        config : dict
            Configuration dictionary
            
        Returns
        -------
        dict
            Configuration with environment variables merged
        """
        def replace_env_vars(obj):
            if isinstance(obj, dict):
                return {k: replace_env_vars(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_env_vars(item) for item in obj]
            elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
                env_var = obj[2:-1]
                return os.getenv(env_var, obj)
            else:
                return obj
        
        # Also check for Looma-specific environment variables
        env_overrides = {}
        for key, value in os.environ.items():
            if key.startswith(ENV_PREFIX):
                # Convert LOOMA_UPDATE_CHANNEL to update.channel
                config_key = key[len(ENV_PREFIX):].lower().replace("_", ".")
                env_overrides[config_key] = value
        
        # Apply environment variable substitutions
        config = replace_env_vars(config)
        
        # Apply environment overrides
        for key_path, value in env_overrides.items():
            keys = key_path.split(".")
            current = config
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            current[keys[-1]] = value
        
        return config
    
    def save(self, config: Dict[str, Any], path: Path, format: str = "yaml") -> None:
        """
        Save configuration to file.
        
        Parameters
        ----------
        config : dict
            Configuration to save
        path : Path
            Path to save file
        format : str
            Output format (yaml, json, toml)
            
        Raises
        ------
        ConfigurationError
            If configuration cannot be saved
        """
        try:
            if not self.validate(config):
                raise ValidationError("Configuration validation failed")
            
            if format == "yaml":
                save_yaml(config, path)
            elif format == "json":
                import json
                with open(path, "w") as f:
                    json.dump(config, f, indent=2)
            elif format == "toml":
                import toml
                with open(path, "w") as f:
                    toml.dump(config, f)
            else:
                raise ValueError(f"Unsupported format: {format}")
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")
    
    def get(self, key: str, default: Any = None, config_data: Optional[Dict[str, Any]] = None) -> Any:
        """
        Get a configuration value by key path.
        
        Parameters
        ----------
        key : str
            Dot-separated key path (e.g., "update.channel")
        default : Any
            Default value if key not found
        config_data : Optional[Dict[str, Any]]
            Configuration data to use instead of self.config
            
        Returns
        -------
        Any
            Configuration value
        """
        keys = key.split(".")
        current = config_data if config_data is not None else self.config
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        
        return current
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value by key path.
        
        Parameters
        ----------
        key : str
            Dot-separated key path (e.g., "update.channel")
        value : Any
            Value to set
        """
        keys = key.split(".")
        current = self.config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def get_platform_config(self, platform: str) -> Dict[str, Any]:
        """
        Get platform-specific configuration.
        
        Parameters
        ----------
        platform : str
            Platform name (windows, macos, linux)
            
        Returns
        -------
        dict
            Platform-specific configuration
        """
        return self.config.get("platforms", {}).get(platform, {})