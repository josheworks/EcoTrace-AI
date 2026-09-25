"""Generic provider for arbitrary AI services."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from ecotrace.capture.request import RequestCapture
from ecotrace.capture.response import ResponseCapture
from ecotrace.providers.base import BaseProvider


class GenericProvider(BaseProvider):
    """Fallback provider for AI services without a dedicated integration.

    Users supply pre-normalized data; the generic provider wraps it
    into EcoTrace's standard format with minimal transformation.
    """

    def __init__(self, provider_name: str = "generic") -> None:
        self._name = provider_name

    @property
    def name(self) -> str:
        return self._name

    def normalize_request(
        self,
        prompt: Union[str, List[Dict[str, Any]]],
        model: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RequestCapture:
        """Wrap user-supplied request data."""
        return RequestCapture(
            prompt=prompt,
            provider=self.name,
            model=model,
            metadata=metadata or {},
        )

    def normalize_response(
        self,
        raw_response: Any,
    ) -> ResponseCapture:
        """Normalize a generic response.

        Accepts a dict with optional keys: response, input_tokens,
        output_tokens, total_tokens, latency_ms.
        """
        if raw_response is None:
            return ResponseCapture()

        if isinstance(raw_response, dict):
            return ResponseCapture(
                response=raw_response.get("response"),
                input_tokens=raw_response.get("input_tokens", 0),
                output_tokens=raw_response.get("output_tokens", 0),
                total_tokens=raw_response.get("total_tokens", 0),
                latency_ms=raw_response.get("latency_ms", 0.0),
                provider_metadata=raw_response,
            )

        if isinstance(raw_response, str):
            return ResponseCapture(response=raw_response)

        return ResponseCapture(response=str(raw_response))
