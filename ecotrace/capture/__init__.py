"""EcoTrace capture layer for request and response data."""

from ecotrace.capture.request import RequestCapture
from ecotrace.capture.response import ResponseCapture

__all__ = ["RequestCapture", "ResponseCapture"]
