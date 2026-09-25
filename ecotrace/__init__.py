"""EcoTrace AI - Production-oriented AI workload observability and optimization SDK.

Core pipeline:
OBSERVE → DETECT → ANALYZE → OPTIMIZE → MEASURE
"""

from ecotrace.client import EcoTrace
from ecotrace.config import EcoTraceConfig
from ecotrace.exceptions import (
    AnalysisError,
    CaptureError,
    ConfigurationError,
    EcoTraceError,
    OptimizationError,
    ProviderError,
    StorageError,
    ValidationError,
)
from ecotrace.integrations.decorators import track
from ecotrace.storage.models import RequestEvent, TrackingResult

__version__ = "0.1.0"

__all__ = [
    "EcoTrace",
    "EcoTraceConfig",
    "RequestEvent",
    "TrackingResult",
    "track",
    # Exceptions
    "EcoTraceError",
    "ConfigurationError",
    "ProviderError",
    "StorageError",
    "ValidationError",
    "CaptureError",
    "AnalysisError",
    "OptimizationError",
]
