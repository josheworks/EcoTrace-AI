"""Abstract storage interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from ecotrace.storage.models import RequestEvent


class BaseStorage(ABC):
    """Abstract base class for EcoTrace event storage backends."""

    @abstractmethod
    def save_event(self, event: RequestEvent) -> None:
        """Persist a request event."""
        ...

    @abstractmethod
    def get_event(self, request_id: str) -> Optional[RequestEvent]:
        """Retrieve a single event by its request ID."""
        ...

    @abstractmethod
    def get_events(
        self,
        session_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[RequestEvent]:
        """Retrieve events with optional filters."""
        ...

    @abstractmethod
    def count_events(
        self,
        session_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> int:
        """Count events matching optional filters."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Remove all stored events."""
        ...
