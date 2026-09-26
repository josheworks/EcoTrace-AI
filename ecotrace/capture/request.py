"""Request capture module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from ecotrace.utils.sanitization import redact_secrets


@dataclass
class RequestCapture:
    """Captures and normalizes AI request data.

    This class extracts the relevant information from a raw AI request
    regardless of provider, producing a normalized representation.

    Attributes:
        prompt: The user prompt string or list of message dicts.
        provider: The AI provider name (e.g., 'openai', 'gemini', 'groq').
        model: The model identifier (e.g., 'gpt-4o-mini').
        metadata: Additional provider-specific or user-supplied metadata.
    """

    prompt: Union[str, List[Dict[str, Any]]]
    provider: str
    model: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Sanitize metadata to remove any secret API keys or credentials."""
        if self.metadata:
            self.metadata = redact_secrets(self.metadata)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "prompt": self.prompt,
            "provider": self.provider,
            "model": self.model,
            "metadata": self.metadata,
        }
