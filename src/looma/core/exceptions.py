"""Custom exceptions for Looma."""


class LoomaError(Exception):
    """
    Base exception for all Looma errors.
    
    Parameters
    ----------
    message : str
        Error message
    code : str, optional
        Error code for identification
    details : dict, optional
        Additional error details
    """
    
    def __init__(self, message: str, code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class ConfigurationError(LoomaError):
    """
    Configuration-related errors.
    
    Raised when there are issues with configuration files,
    validation, or environment variables.
    """
    pass


class PackagingError(LoomaError):
    """
    Packaging-related errors.
    
    Raised when there are issues during the packaging process
    with any of the supported engines.
    """
    pass


class UpdateError(LoomaError):
    """
    Update-related errors.
    
    Raised when there are issues with checking, downloading,
    or applying updates.
    """
    pass


class SecurityError(LoomaError):
    """
    Security-related errors.
    
    Raised when there are issues with signatures, verification,
    or encryption.
    """
    pass


class NetworkError(LoomaError):
    """
    Network-related errors.
    
    Raised when there are issues with network connectivity,
    downloads, or API calls.
    """
    pass


class ValidationError(ConfigurationError):
    """
    Validation errors.
    
    Raised when configuration or input validation fails.
    """
    pass


class NotFoundError(LoomaError):
    """
    Resource not found errors.
    
    Raised when a required resource cannot be found.
    """
    pass


class PermissionError(LoomaError):
    """
    Permission-related errors.
    
    Raised when there are insufficient permissions for an operation.
    """
    pass


class TimeoutError(NetworkError):
    """
    Timeout errors.
    
    Raised when an operation exceeds the configured timeout.
    """
    pass