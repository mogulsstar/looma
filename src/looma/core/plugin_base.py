"""Base plugin interface for Looma - simplified and practical."""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional


class PluginInterface(ABC):
    """Simple plugin interface that components can implement."""
    
    @abstractmethod
    def get_schema_file(self) -> Optional[Path]:
        """
        Get the path to JSON schema file for this plugin.
        
        Returns
        -------
        Optional[Path]
            Path to schema file if available
        """
        pass
    
    def load_schema(self) -> Optional[Dict[str, Any]]:
        """
        Load JSON schema for configuration validation.
        
        Returns
        -------
        Optional[dict]
            JSON schema if available
        """
        schema_file = self.get_schema_file()
        if schema_file and schema_file.exists():
            with open(schema_file, 'r') as f:
                return json.load(f)
        return None
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration against schema.
        
        Parameters
        ----------
        config : dict
            Configuration to validate
            
        Returns
        -------
        bool
            True if valid or no schema available
        """
        schema = self.load_schema()
        if not schema:
            return True
        
        try:
            import jsonschema
            jsonschema.validate(config, schema)
            return True
        except jsonschema.ValidationError:
            return False
        except ImportError:
            # If jsonschema not installed, skip validation
            return True