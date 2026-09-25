"""Google Gemini provider implementation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from ecotrace.capture.request import RequestCapture
from ecotrace.capture.response import ResponseCapture
from ecotrace.providers.base import BaseProvider


class GeminiProvider(BaseProvider):
    """Provider integration for Google Gemini.

    Normalizes Gemini-specific request/response formats into
    EcoTrace's provider-agnostic data model.
    """

    @property
    def name(self) -> str:
        return "gemini"

    def normalize_request(
        self,
        prompt: Union[str, List[Dict[str, Any]]],
        model: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RequestCapture:
        """Normalize a Gemini request."""
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
        """Normalize a Gemini API response.

        Expects a dict-like or Gemini response object.
        """
        if isinstance(raw_response, str):
            return ResponseCapture(response=raw_response)

        if isinstance(raw_response, dict):

            usage = raw_response.get("usage_metadata", {})
            candidates = raw_response.get("candidates", [])
            content = None
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    content = parts[0].get("text")
            return ResponseCapture(
                response=content,
                input_tokens=usage.get("prompt_token_count", 0),
                output_tokens=usage.get("candidates_token_count", 0),
                total_tokens=usage.get("total_token_count", 0),
                provider_metadata=raw_response,
            )

        # Support Gemini SDK response objects
        try:
            usage = getattr(raw_response, "usage_metadata", None)
            text = getattr(raw_response, "text", None)
            return ResponseCapture(
                response=text,
                input_tokens=getattr(usage, "prompt_token_count", 0) if usage else 0,
                output_tokens=getattr(usage, "candidates_token_count", 0) if usage else 0,
                total_tokens=getattr(usage, "total_token_count", 0) if usage else 0,
            )
        except (AttributeError, IndexError):
            return ResponseCapture(provider_metadata={"raw": str(raw_response)})
