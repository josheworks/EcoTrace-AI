"""Response capture module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ResponseCapture:
    """Captures and normalizes AI response data.

    This class extracts relevant information from a raw AI response
    regardless of provider, producing a normalized representation.

    Attributes:
        response: The text content of the AI response.
        input_tokens: Number of tokens in the input/prompt.
        output_tokens: Number of tokens in the output/response.
        total_tokens: Total tokens consumed (input + output).
        latency_ms: Response latency in milliseconds.
        provider_metadata: Raw provider-specific response metadata.
    """

    response: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    provider_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Calculate total tokens if not explicitly provided."""
        if self.total_tokens == 0 and (self.input_tokens or self.output_tokens):
            self.total_tokens = self.input_tokens + self.output_tokens

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "response": self.response,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
            "provider_metadata": self.provider_metadata,
        }
