"""Validators for Looma GUI inputs."""

import re
from pathlib import Path
from typing import Any, Optional

import wx


class BaseValidator(wx.Validator):
    """
    Base validator class.
    
    Attributes
    ----------
    error_message : str
        Error message to display
    """
    
    def __init__(self, error_message: str = "Invalid input"):
        """
        Initialize validator.
        
        Parameters
        ----------
        error_message : str
            Error message
        """
        super().__init__()
        self.error_message = error_message
    
    def Clone(self):
        """Clone validator."""
        return self.__class__(self.error_message)
    
    def Validate(self, parent) -> bool:
        """
        Validate control value.
        
        Parameters
        ----------
        parent : wx.Window
            Parent window
            
        Returns
        -------
        bool
            True if valid
        """
        return True
    
    def TransferToWindow(self) -> bool:
        """Transfer data to window."""
        return True
    
    def TransferFromWindow(self) -> bool:
        """Transfer data from window."""
        return True
    
    def _show_error(self):
        """Show error message."""
        wx.MessageBox(
            self.error_message,
            "Validation Error",
            wx.OK | wx.ICON_ERROR,
        )


class RequiredValidator(BaseValidator):
    """Validator for required fields."""
    
    def __init__(self):
        """Initialize required validator."""
        super().__init__("This field is required")
    
    def Validate(self, parent) -> bool:
        """
        Validate that field is not empty.
        
        Parameters
        ----------
        parent : wx.Window
            Parent window
            
        Returns
        -------
        bool
            True if not empty
        """
        ctrl = self.GetWindow()
        
        if isinstance(ctrl, wx.TextCtrl):
            value = ctrl.GetValue().strip()
            if not value:
                self._show_error()
                ctrl.SetFocus()
                return False
        
        return True


class EmailValidator(BaseValidator):
    """Validator for email addresses."""
    
    def __init__(self):
        """Initialize email validator."""
        super().__init__("Invalid email address")
        self.pattern = re.compile(
            r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        )
    
    def Validate(self, parent) -> bool:
        """
        Validate email format.
        
        Parameters
        ----------
        parent : wx.Window
            Parent window
            
        Returns
        -------
        bool
            True if valid email
        """
        ctrl = self.GetWindow()
        
        if isinstance(ctrl, wx.TextCtrl):
            value = ctrl.GetValue().strip()
            if value and not self.pattern.match(value):
                self._show_error()
                ctrl.SetFocus()
                return False
        
        return True


class VersionValidator(BaseValidator):
    """Validator for version strings."""
    
    def __init__(self):
        """Initialize version validator."""
        super().__init__("Invalid version format (e.g., 1.0.0)")
        self.pattern = re.compile(
            r"^\d+\.\d+(\.\d+)?(-[a-zA-Z0-9]+)?(\+[a-zA-Z0-9]+)?$"
        )
    
    def Validate(self, parent) -> bool:
        """
        Validate version format.
        
        Parameters
        ----------
        parent : wx.Window
            Parent window
            
        Returns
        -------
        bool
            True if valid version
        """
        ctrl = self.GetWindow()
        
        if isinstance(ctrl, wx.TextCtrl):
            value = ctrl.GetValue().strip()
            if value and not self.pattern.match(value):
                self._show_error()
                ctrl.SetFocus()
                return False
        
        return True


class PathValidator(BaseValidator):
    """Validator for file/directory paths."""
    
    def __init__(
        self,
        must_exist: bool = False,
        is_directory: bool = False,
        extensions: Optional[list] = None,
    ):
        """
        Initialize path validator.
        
        Parameters
        ----------
        must_exist : bool
            Path must exist
        is_directory : bool
            Path must be directory
        extensions : Optional[list]
            Allowed file extensions
        """
        super().__init__("Invalid path")
        self.must_exist = must_exist
        self.is_directory = is_directory
        self.extensions = extensions
    
    def Clone(self):
        """Clone validator."""
        return PathValidator(self.must_exist, self.is_directory, self.extensions)
    
    def Validate(self, parent) -> bool:
        """
        Validate path.
        
        Parameters
        ----------
        parent : wx.Window
            Parent window
            
        Returns
        -------
        bool
            True if valid path
        """
        ctrl = self.GetWindow()
        
        if isinstance(ctrl, wx.TextCtrl):
            value = ctrl.GetValue().strip()
            
            if not value:
                return True  # Empty is allowed
            
            path = Path(value)
            
            # Check if path exists
            if self.must_exist and not path.exists():
                self.error_message = f"Path does not exist: {value}"
                self._show_error()
                ctrl.SetFocus()
                return False
            
            # Check if directory
            if self.must_exist and self.is_directory and not path.is_dir():
                self.error_message = f"Path is not a directory: {value}"
                self._show_error()
                ctrl.SetFocus()
                return False
            
            # Check extension
            if self.extensions and path.suffix not in self.extensions:
                self.error_message = f"Invalid file extension. Allowed: {', '.join(self.extensions)}"
                self._show_error()
                ctrl.SetFocus()
                return False
        
        return True


class URLValidator(BaseValidator):
    """Validator for URLs."""
    
    def __init__(self, require_https: bool = False):
        """
        Initialize URL validator.
        
        Parameters
        ----------
        require_https : bool
            Require HTTPS URLs
        """
        super().__init__("Invalid URL")
        self.require_https = require_https
        self.pattern = re.compile(
            r"^https?://[a-zA-Z0-9.-]+(?:\.[a-zA-Z]{2,})+(?:/[^?]*)?(?:\?.*)?$"
        )
    
    def Clone(self):
        """Clone validator."""
        return URLValidator(self.require_https)
    
    def Validate(self, parent) -> bool:
        """
        Validate URL format.
        
        Parameters
        ----------
        parent : wx.Window
            Parent window
            
        Returns
        -------
        bool
            True if valid URL
        """
        ctrl = self.GetWindow()
        
        if isinstance(ctrl, wx.TextCtrl):
            value = ctrl.GetValue().strip()
            
            if not value:
                return True  # Empty is allowed
            
            if not self.pattern.match(value):
                self._show_error()
                ctrl.SetFocus()
                return False
            
            if self.require_https and not value.startswith("https://"):
                self.error_message = "URL must use HTTPS"
                self._show_error()
                ctrl.SetFocus()
                return False
        
        return True


class IntegerValidator(BaseValidator):
    """Validator for integer values."""
    
    def __init__(
        self,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
    ):
        """
        Initialize integer validator.
        
        Parameters
        ----------
        min_value : Optional[int]
            Minimum value
        max_value : Optional[int]
            Maximum value
        """
        super().__init__("Invalid integer value")
        self.min_value = min_value
        self.max_value = max_value
    
    def Clone(self):
        """Clone validator."""
        return IntegerValidator(self.min_value, self.max_value)
    
    def Validate(self, parent) -> bool:
        """
        Validate integer value.
        
        Parameters
        ----------
        parent : wx.Window
            Parent window
            
        Returns
        -------
        bool
            True if valid integer
        """
        ctrl = self.GetWindow()
        
        if isinstance(ctrl, wx.TextCtrl):
            value = ctrl.GetValue().strip()
            
            if not value:
                return True  # Empty is allowed
            
            try:
                int_value = int(value)
                
                if self.min_value is not None and int_value < self.min_value:
                    self.error_message = f"Value must be at least {self.min_value}"
                    self._show_error()
                    ctrl.SetFocus()
                    return False
                
                if self.max_value is not None and int_value > self.max_value:
                    self.error_message = f"Value must be at most {self.max_value}"
                    self._show_error()
                    ctrl.SetFocus()
                    return False
                
            except ValueError:
                self._show_error()
                ctrl.SetFocus()
                return False
        
        return True


class RegexValidator(BaseValidator):
    """Validator using regular expressions."""
    
    def __init__(self, pattern: str, error_message: str):
        """
        Initialize regex validator.
        
        Parameters
        ----------
        pattern : str
            Regular expression pattern
        error_message : str
            Error message
        """
        super().__init__(error_message)
        self.pattern = re.compile(pattern)
    
    def Clone(self):
        """Clone validator."""
        return RegexValidator(self.pattern.pattern, self.error_message)
    
    def Validate(self, parent) -> bool:
        """
        Validate using regex.
        
        Parameters
        ----------
        parent : wx.Window
            Parent window
            
        Returns
        -------
        bool
            True if matches pattern
        """
        ctrl = self.GetWindow()
        
        if isinstance(ctrl, wx.TextCtrl):
            value = ctrl.GetValue().strip()
            
            if value and not self.pattern.match(value):
                self._show_error()
                ctrl.SetFocus()
                return False
        
        return True


class CompositeValidator(BaseValidator):
    """Validator that combines multiple validators."""
    
    def __init__(self, validators: list):
        """
        Initialize composite validator.
        
        Parameters
        ----------
        validators : list
            List of validators
        """
        super().__init__("Validation failed")
        self.validators = validators
    
    def Clone(self):
        """Clone validator."""
        cloned_validators = [v.Clone() for v in self.validators]
        return CompositeValidator(cloned_validators)
    
    def Validate(self, parent) -> bool:
        """
        Validate using all validators.
        
        Parameters
        ----------
        parent : wx.Window
            Parent window
            
        Returns
        -------
        bool
            True if all validators pass
        """
        for validator in self.validators:
            # Set window for each validator
            validator.SetWindow(self.GetWindow())
            
            if not validator.Validate(parent):
                return False
        
        return True


def validate_config_field(field_name: str, value: Any) -> bool:
    """
    Validate configuration field.
    
    Parameters
    ----------
    field_name : str
        Field name
    value : Any
        Field value
        
    Returns
    -------
    bool
        True if valid
    """
    # Version fields
    if "version" in field_name.lower():
        pattern = re.compile(r"^\d+\.\d+(\.\d+)?(-[a-zA-Z0-9]+)?(\+[a-zA-Z0-9]+)?$")
        return bool(pattern.match(str(value)))
    
    # Email fields
    if "email" in field_name.lower():
        pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        return bool(pattern.match(str(value)))
    
    # URL fields
    if "url" in field_name.lower() or "endpoint" in field_name.lower():
        pattern = re.compile(r"^https?://[a-zA-Z0-9.-]+(?:\.[a-zA-Z]{2,})+(?:/.*)?$")
        return bool(pattern.match(str(value)))
    
    # Path fields
    if "path" in field_name.lower() or "dir" in field_name.lower():
        # Basic path validation
        return len(str(value)) > 0
    
    # Port fields
    if "port" in field_name.lower():
        try:
            port = int(value)
            return 1 <= port <= 65535
        except (ValueError, TypeError):
            return False
    
    # Default: allow any non-empty value
    return value is not None and str(value).strip() != ""