"""EcoTrace custom exceptions."""


class EcoTraceError(Exception):
    """Base exception for all EcoTrace errors."""
    pass


class ConfigurationError(EcoTraceError):
    """Raised when EcoTrace configuration is invalid."""
    pass


class ProviderError(EcoTraceError):
    """Raised when a provider operation fails."""
    pass


class StorageError(EcoTraceError):
    """Raised when a storage operation fails."""
    pass


class ValidationError(EcoTraceError):
    """Raised when input validation fails."""
    pass


class CaptureError(EcoTraceError):
    """Raised when request/response capture fails."""
    pass


class AnalysisError(EcoTraceError):
    """Raised when analysis operations fail."""
    pass


class OptimizationError(EcoTraceError):
    """Raised when optimization operations fail."""
    pass
