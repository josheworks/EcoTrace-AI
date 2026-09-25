"""Core data models for EcoTrace."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union


def _generate_id() -> str:
    return uuid.uuid4().hex


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class RequestEvent:
    """Normalized AI request event.

    This is the core data model consumed by all analysis, optimization,
    and impact modules. It is provider-agnostic.

    Attributes:
        request_id: Unique identifier for this request.
        session_id: Session this request belongs to.
        timestamp: When the request was made (UTC).
        provider: AI provider name (e.g. 'openai', 'gemini').
        model: Model identifier (e.g. 'gpt-4o-mini').
        prompt: The input prompt or message list.
        response: The model's text response.
        input_tokens: Number of input/prompt tokens.
        output_tokens: Number of output/completion tokens.
        total_tokens: Total tokens consumed.
        latency_ms: End-to-end latency in milliseconds.
        request_hash: Deterministic hash of the request for deduplication.
        metadata: Arbitrary metadata dict.
    """

    provider: str
    model: str
    prompt: Union[str, List[Dict[str, Any]]]
    request_id: str = field(default_factory=_generate_id)
    session_id: Optional[str] = None
    timestamp: datetime = field(default_factory=_utc_now)
    response: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    request_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the event to a plain dictionary."""
        return {
            "request_id": self.request_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "provider": self.provider,
            "model": self.model,
            "prompt": self.prompt,
            "response": self.response,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
            "request_hash": self.request_hash,
            "metadata": self.metadata,
        }


@dataclass
class TrackingResult:
    """Result returned from a tracking operation.

    Wraps a RequestEvent with additional tracking metadata.
    """

    event: RequestEvent
    is_duplicate: bool = False
    duplicate_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the result."""
        return {
            "event": self.event.to_dict(),
            "is_duplicate": self.is_duplicate,
            "duplicate_count": self.duplicate_count,
            "metadata": self.metadata,
        }
