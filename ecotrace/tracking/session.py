"""Session management for tracking."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _generate_session_id() -> str:
    return uuid.uuid4().hex


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Session:
    """Represents a tracking session.

    A session groups related AI requests together.

    Attributes:
        session_id: Unique session identifier.
        project: Optional project name.
        started_at: Session start timestamp.
        metadata: Arbitrary session metadata.
        event_count: Number of events tracked in this session.
    """

    session_id: str = field(default_factory=_generate_session_id)
    project: Optional[str] = None
    started_at: datetime = field(default_factory=_utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    event_count: int = 0

    def increment(self) -> None:
        """Increment the event counter."""
        self.event_count += 1
