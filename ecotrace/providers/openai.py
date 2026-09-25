"""OpenAI provider implementation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from ecotrace.capture.request import RequestCapture
from ecotrace.capture.response import ResponseCapture
from ecotrace.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    """Provider integration for OpenAI.

    Normalizes OpenAI-specific request/response formats into
    EcoTrace's provider-agnostic data model.
    """

    @property
    def name(self) -> str:
        return "openai"

    def normalize_request(
        self,
        prompt: Union[str, List[Dict[str, Any]]],
        model: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RequestCapture:
        """Normalize an OpenAI request."""
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt

        return RequestCapture(
            prompt=messages,
            provider=self.name,
            model=model,
            metadata=metadata or {},
        )

    def normalize_response(
        self,
        raw_response: Any,
    ) -> ResponseCapture:
        """Normalize an OpenAI API response.

        Expects a dict-like object or an OpenAI response object with
        usage and choices attributes. Falls back gracefully if the
        structure is unexpected.
        """
        if isinstance(raw_response, str):
            return ResponseCapture(response=raw_response)

        # Support dict responses (e.g. from testing or JSON mode)
        if isinstance(raw_response, dict):

            usage = raw_response.get("usage", {})
            choices = raw_response.get("choices", [])
            content = None
            if choices:
                message = choices[0].get("message", {})
                content = message.get("content")
            return ResponseCapture(
                response=content,
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                provider_metadata=raw_response,
            )

        # Support OpenAI SDK response objects
        try:
            usage = getattr(raw_response, "usage", None)
            choices = getattr(raw_response, "choices", [])
            content = None
            if choices:
                content = getattr(choices[0].message, "content", None)
            return ResponseCapture(
                response=content,
                input_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
                output_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
                total_tokens=getattr(usage, "total_tokens", 0) if usage else 0,
            )
        except (AttributeError, IndexError):
            return ResponseCapture(provider_metadata={"raw": str(raw_response)})
